"""Tests for /api/v1/core/alertas endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_alerts_empty(client, auth_headers):
    resp = await client.get("/api/v1/core/alertas", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert body["meta"]["total"] >= 0


@pytest.mark.asyncio
async def test_create_and_list_alerts(client, auth_headers, db_session):
    """Seed alerts via DB, then list."""
    import uuid

    from app.models.smart_alert import SmartAlert

    for i, tipo in enumerate(["hot_lead", "stalled_deal", "churn_risk"]):
        db_session.add(SmartAlert(
            tenant_id=uuid.UUID(auth_headers["X-Tenant-ID"]),
            tipo=tipo,
            mensaje=f"Test alert {i}",
            leido=(i == 0),
        ))
    await db_session.commit()

    resp = await client.get("/api/v1/core/alertas", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["meta"]["total"] >= 3


@pytest.mark.asyncio
async def test_list_alerts_filter_tipo(client, auth_headers, db_session):
    import uuid

    from app.models.smart_alert import SmartAlert

    db_session.add(SmartAlert(
        tenant_id=uuid.UUID(auth_headers["X-Tenant-ID"]),
        tipo="hot_lead",
        mensaje="hot",
        leido=False,
    ))
    db_session.add(SmartAlert(
        tenant_id=uuid.UUID(auth_headers["X-Tenant-ID"]),
        tipo="churn_risk",
        mensaje="churn",
        leido=False,
    ))
    await db_session.commit()

    resp = await client.get(
        "/api/v1/core/alertas?tipo=hot_lead", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    for alert in body["data"]:
        assert alert["tipo"] == "hot_lead"


@pytest.mark.asyncio
async def test_mark_alert_read(client, auth_headers, db_session):
    import uuid

    from app.models.smart_alert import SmartAlert

    alert = SmartAlert(
        tenant_id=uuid.UUID(auth_headers["X-Tenant-ID"]),
        tipo="stalled_deal",
        mensaje="stalled",
        leido=False,
    )
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)

    resp = await client.patch(
        f"/api/v1/core/alertas/{alert.id}",
        headers=auth_headers,
        json={"leido": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["leido"] is True


@pytest.mark.asyncio
async def test_list_alerts_requires_auth(client):
    resp = await client.get("/api/v1/core/alertas")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_alerts_pagination(client, auth_headers):
    resp = await client.get(
        "/api/v1/core/alertas?page=1&page_size=2", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["page"] == 1
    assert body["meta"]["page_size"] == 2
    assert len(body["data"]) <= 2
