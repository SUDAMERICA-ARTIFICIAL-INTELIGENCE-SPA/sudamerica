"""Tests for GET /api/v1/mesas/disponibilidad."""

import os
import uuid
from datetime import date, datetime, time, timedelta, timezone

import jwt
import pytest
from sqlalchemy import delete

from shared.models.mesa import Mesa
from app.models.reservacion import Reservacion

from .conftest import TENANT_ID


def _build_service_headers() -> dict[str, str]:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "iss": "ai_dialer",
            "sub": "ai_dialer",
            "aud": "api_execute",
            "tenant_id": TENANT_ID,
            "type": "service",
            "role": "ADMIN",
            "scopes": ["reservaciones:read"],
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": now + timedelta(hours=1),
        },
        os.environ["AI_DIALER_INTERNAL_SERVICE_SECRET_KEY"],
        algorithm="HS256",
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
    }


async def _seed_mesa(db_session, *, numero: int, capacidad: int, nombre: str | None = None) -> Mesa:
    mesa = Mesa(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(TENANT_ID),
        numero=numero,
        capacidad=capacidad,
        nombre=nombre,
        qr_token=f"qr-{numero}-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(mesa)
    await db_session.commit()
    return mesa


async def _clear_availability_data(db_session) -> None:
    tenant_uuid = uuid.UUID(TENANT_ID)
    await db_session.execute(
        delete(Reservacion).where(Reservacion.tenant_id == tenant_uuid)
    )
    await db_session.execute(
        delete(Mesa).where(Mesa.tenant_id == tenant_uuid)
    )
    await db_session.commit()


async def _seed_reservacion(
    db_session,
    *,
    mesa_id: uuid.UUID,
    fecha_reserva: date,
    hora_inicio: time,
    hora_fin: time,
    estado: str = "PENDIENTE",
) -> Reservacion:
    reservacion = Reservacion(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(TENANT_ID),
        mesa_id=mesa_id,
        fecha_reserva=fecha_reserva,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        cantidad_personas=4,
        nombre_cliente="Reserva Test",
        estado=estado,
    )
    db_session.add(reservacion)
    await db_session.commit()
    return reservacion


@pytest.mark.asyncio
async def test_disponibilidad_returns_available_mesa(client, auth_headers, db_session):
    await _clear_availability_data(db_session)
    mesa = await _seed_mesa(db_session, numero=101, capacidad=6, nombre="terraza")

    resp = await client.get(
        "/api/v1/mesas/disponibilidad",
        params={"fecha": "2026-04-05", "hora": "20:00", "personas": 4},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["personas"] == 4
    assert data["disponibles"] == [{
        "id": str(mesa.id),
        "numero": 101,
        "capacidad": 6,
        "zona": "terraza",
    }]
    assert data["mesas"] == [{
        "id": str(mesa.id),
        "mesa_id": str(mesa.id),
        "numero": 101,
        "capacidad": 6,
        "zona": "terraza",
    }]


@pytest.mark.asyncio
async def test_disponibilidad_excludes_conflicting_reservation(client, auth_headers, db_session):
    await _clear_availability_data(db_session)
    mesa = await _seed_mesa(db_session, numero=102, capacidad=6, nombre="interior")
    await _seed_reservacion(
        db_session,
        mesa_id=mesa.id,
        fecha_reserva=date(2026, 4, 5),
        hora_inicio=time(19, 30),
        hora_fin=time(21, 0),
    )

    resp = await client.get(
        "/api/v1/mesas/disponibilidad",
        params={"fecha": "2026-04-05", "hora": "20:00", "personas": 4},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["disponibles"] == []


@pytest.mark.asyncio
async def test_disponibilidad_excludes_insufficient_capacity(client, auth_headers, db_session):
    await _clear_availability_data(db_session)
    await _seed_mesa(db_session, numero=103, capacidad=2, nombre="barra")

    resp = await client.get(
        "/api/v1/mesas/disponibilidad",
        params={"fecha": "2026-04-05", "hora": "20:00", "personas": 4},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["disponibles"] == []


@pytest.mark.asyncio
async def test_disponibilidad_returns_empty_list_when_no_matches(client, auth_headers, db_session):
    await _clear_availability_data(db_session)
    resp = await client.get(
        "/api/v1/mesas/disponibilidad",
        params={"fecha": "2026-04-05", "hora": "20:00", "personas": 8},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["disponibles"] == []
    assert data["mesas"] == []


@pytest.mark.asyncio
async def test_disponibilidad_accepts_ai_dialer_service_token(client, db_session):
    await _clear_availability_data(db_session)
    mesa = await _seed_mesa(db_session, numero=104, capacidad=4, nombre="salon")

    resp = await client.get(
        "/api/v1/mesas/disponibilidad",
        params={"fecha": "2026-04-05", "hora": "20:00", "personas": 4},
        headers=_build_service_headers(),
    )

    assert resp.status_code == 200
    assert resp.json()["disponibles"][0]["id"] == str(mesa.id)
