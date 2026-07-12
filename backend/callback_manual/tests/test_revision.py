"""Tests for revision humana endpoints."""

from datetime import datetime, timedelta, timezone
import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from shared.middleware.auth import create_service_token

from app.services import revision_service
from .conftest import TENANT_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _revision_payload(confianza=0.72, lead_id=None):
    return {
        "lead_id": str(lead_id) if lead_id else None,
        "mensaje_original": "Quiero saber el precio del producto X",
        "respuesta_ia": "El precio del producto X es $100 USD",
        "confianza": confianza,
    }


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_revision(client, auth_headers):
    """POST /api/v1/revision creates a pending review."""
    payload = _revision_payload()
    response = await client.post("/api/v1/reviews", json=payload, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["mensaje_original"] == payload["mensaje_original"]
    assert body["procesado"] is False
    assert body["confianza"] == pytest.approx(0.72, abs=0.001)


@pytest.mark.asyncio
async def test_create_revision_rejects_confianza_out_of_range(client, auth_headers):
    payload = _revision_payload(confianza=1.5)
    response = await client.post("/api/v1/reviews", json=payload, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_revision_rejects_service_token(client):
    """Review creation is users-only (ADMIN/ASESOR panel); a well-formed token
    from a trusted issuer must still be rejected. Guards against the AI_dialer
    removal silently widening access to any service with reviews:create scope."""
    token = create_service_token(
        service_name="tasks",
        audience="callback_manual",
        tenant_id=TENANT_ID,
        signing_key=os.environ["TASKS_INTERNAL_SERVICE_SECRET_KEY"],
        scopes=("reviews:create",),
        expires_in_seconds=300,
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(TENANT_ID),
    }
    payload = _revision_payload()
    payload["lead_id"] = None
    response = await client.post("/api/v1/reviews", json=payload, headers=headers)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# List pendientes
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_pendientes(client, auth_headers):
    """GET /api/v1/revision/pendientes returns paginated pending reviews."""
    # Create two reviews
    await client.post("/api/v1/reviews", json=_revision_payload(), headers=auth_headers)
    await client.post("/api/v1/reviews", json=_revision_payload(), headers=auth_headers)

    response = await client.get("/api/v1/reviews/pendientes", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] >= 2
    assert len(body["data"]) >= 2
    assert body["meta"]["page"] == 1


@pytest.mark.asyncio
async def test_list_pendientes_unauthorized(client):
    """GET /api/v1/revision/pendientes without auth returns 403 or 401."""
    response = await client.get("/api/v1/reviews/pendientes")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Aprobar
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("app.services.revision_service._notify_tasks", new_callable=AsyncMock)
async def test_aprobar(mock_notify, client, auth_headers):
    """POST /api/v1/revision/{id}/aprobar marks review as approved."""
    create_resp = await client.post("/api/v1/reviews", json=_revision_payload(), headers=auth_headers)
    revision_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/reviews/{revision_id}/aprobar?tiempo_ms=1500",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accion"] == "APROBAR"
    assert body["procesado"] is True
    assert body["tiempo_revision_ms"] == 1500
    mock_notify.assert_awaited_once()


# ---------------------------------------------------------------------------
# Editar
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("app.services.revision_service._notify_tasks", new_callable=AsyncMock)
async def test_editar(mock_notify, client, auth_headers):
    """POST /api/v1/revision/{id}/editar saves edited response."""
    create_resp = await client.post("/api/v1/reviews", json=_revision_payload(), headers=auth_headers)
    revision_id = create_resp.json()["id"]

    body_req = {
        "accion": "EDITAR",
        "respuesta_editada": "El precio correcto es $95 USD",
    }
    response = await client.post(
        f"/api/v1/reviews/{revision_id}/editar?tiempo_ms=3200",
        json=body_req,
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accion"] == "EDITAR"
    assert body["respuesta_editada"] == "El precio correcto es $95 USD"
    assert body["procesado"] is True
    mock_notify.assert_awaited_once()


@pytest.mark.asyncio
async def test_editar_requires_respuesta_editada(client, auth_headers):
    """POST /api/v1/revision/{id}/editar fails without respuesta_editada."""
    create_resp = await client.post("/api/v1/reviews", json=_revision_payload(), headers=auth_headers)
    revision_id = create_resp.json()["id"]

    body_req = {"accion": "EDITAR"}
    response = await client.post(
        f"/api/v1/reviews/{revision_id}/editar",
        json=body_req,
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_editar_rejects_non_edit_action(client, auth_headers):
    create_resp = await client.post("/api/v1/reviews", json=_revision_payload(), headers=auth_headers)
    revision_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/reviews/{revision_id}/editar",
        json={"accion": "RECHAZAR", "respuesta_editada": "No deberia aceptar esto"},
        headers=auth_headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Rechazar
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_rechazar(client, auth_headers):
    """POST /api/v1/revision/{id}/rechazar marks review as rejected."""
    create_resp = await client.post("/api/v1/reviews", json=_revision_payload(), headers=auth_headers)
    revision_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/reviews/{revision_id}/rechazar?tiempo_ms=500",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accion"] == "RECHAZAR"
    assert body["procesado"] is True


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_stats(client, auth_headers):
    """GET /api/v1/revision/stats returns aggregated statistics."""
    response = await client.get("/api/v1/reviews/stats", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "total_pendientes" in body
    assert "aprobadas_hoy" in body
    assert "editadas_hoy" in body
    assert "rechazadas_hoy" in body
    assert "precision_ia" in body


@pytest.mark.asyncio
@patch("app.services.revision_service._notify_tasks", new_callable=AsyncMock)
async def test_stats_average_revision_time_is_not_cartesian_product(mock_notify, client, auth_headers):
    payload = _revision_payload()
    payload["lead_id"] = None
    first = await client.post("/api/v1/reviews", json=payload, headers=auth_headers)
    second = await client.post("/api/v1/reviews", json=payload, headers=auth_headers)

    first_id = first.json()["id"]
    second_id = second.json()["id"]

    await client.post(f"/api/v1/reviews/{first_id}/aprobar?tiempo_ms=1000", headers=auth_headers)
    await client.post(
        f"/api/v1/reviews/{second_id}/editar?tiempo_ms=3000",
        json={"accion": "EDITAR", "respuesta_editada": "Respuesta corregida"},
        headers=auth_headers,
    )

    response = await client.get("/api/v1/reviews/stats", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["tiempo_promedio_ms"] == pytest.approx(2000.0)


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_aprobar_not_found(client, auth_headers):
    """POST /api/v1/revision/{id}/aprobar with invalid ID returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.post(
        f"/api/v1/reviews/{fake_id}/aprobar",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_aprobar_conflicts_when_revision_is_already_claimed(client, auth_headers, session_factory):
    create_resp = await client.post("/api/v1/reviews", json=_revision_payload(), headers=auth_headers)
    revision_id = uuid.UUID(create_resp.json()["id"])

    async with session_factory() as session:
        await revision_service._claim_revision(
            session=session,
            tenant_id=TENANT_ID,
            revision_id=revision_id,
            operador_id=uuid.uuid4(),
        )

    response = await client.post(
        f"/api/v1/reviews/{revision_id}/aprobar",
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_claim_revision_recovers_stale_claim(client, auth_headers, session_factory):
    create_resp = await client.post("/api/v1/reviews", json=_revision_payload(), headers=auth_headers)
    revision_id = uuid.UUID(create_resp.json()["id"])

    async with session_factory() as session:
        revision = await revision_service._get_revision(session, TENANT_ID, revision_id)
        revision.operador_id = uuid.uuid4()
        revision.updated_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        await session.commit()

    async with session_factory() as session:
        revision = await revision_service._claim_revision(
            session=session,
            tenant_id=TENANT_ID,
            revision_id=revision_id,
            operador_id=uuid.uuid4(),
        )

    assert revision.operador_id is not None
