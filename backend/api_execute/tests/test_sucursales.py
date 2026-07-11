"""Tests for sucursales CRUD endpoints."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete

from shared.models.sucursal import Sucursal
from .conftest import TENANT_ID, TestSessionFactory, make_token


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _admin_headers(tenant_id: str = TENANT_ID) -> dict:
    token = make_token(tenant_id=tenant_id, role="ADMIN")
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


def _viewer_headers(tenant_id: str = TENANT_ID) -> dict:
    token = make_token(tenant_id=tenant_id, role="VIEWER")
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


BASE = "/api/v1/core/sucursales"


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_sucursales():
    """Clean up sucursales between tests to avoid cross-test state."""
    yield
    async with TestSessionFactory() as session:
        await session.execute(delete(Sucursal))
        await session.commit()


# ─── CREATE ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_first_sucursal_auto_principal(client: AsyncClient):
    """First sucursal should be auto-set as principal."""
    resp = await client.post(
        BASE,
        json={"nombre": "Sucursal Centro"},
        headers=_admin_headers(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Sucursal Centro"
    assert data["es_principal"] is True
    assert data["activo"] is True
    assert "slug" in data


@pytest.mark.asyncio
async def test_create_sucursal_requires_admin(client: AsyncClient):
    """VIEWER cannot create sucursales."""
    resp = await client.post(
        BASE,
        json={"nombre": "Sucursal Norte"},
        headers=_viewer_headers(),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_sucursal_plan_limit_estandar(client: AsyncClient):
    """ESTANDAR plan allows max 1 sucursal (the first one); 2nd should fail."""
    headers = _admin_headers()
    resp1 = await client.post(
        BASE, json={"nombre": "Primera"}, headers=headers
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        BASE, json={"nombre": "Segunda"}, headers=headers
    )
    assert resp2.status_code == 403


@pytest.mark.asyncio
async def test_create_sucursal_pro_allows_multiple(client: AsyncClient):
    """PRO plan allows multiple sucursales."""
    from app.models.tenant import Tenant
    from sqlalchemy import select

    # Upgrade tenant to PRO
    async with TestSessionFactory() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(TENANT_ID))
        )
        tenant = result.scalar_one()
        tenant.plan = "PRO"
        await session.commit()

    headers = _admin_headers()
    resp1 = await client.post(
        BASE, json={"nombre": "Central"}, headers=headers
    )
    assert resp1.status_code == 201
    assert resp1.json()["es_principal"] is True

    resp2 = await client.post(
        BASE, json={"nombre": "Norte"}, headers=headers
    )
    assert resp2.status_code == 201
    assert resp2.json()["es_principal"] is False


# ─── LIST ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_sucursales_empty(client: AsyncClient):
    """List returns empty when no sucursales exist."""
    resp = await client.get(BASE, headers=_admin_headers())
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_sucursales_returns_created(client: AsyncClient):
    """After creating a sucursal, it appears in the list."""
    headers = _admin_headers()
    await client.post(BASE, json={"nombre": "Test List"}, headers=headers)
    resp = await client.get(BASE, headers=headers)
    assert resp.status_code == 200
    names = [s["nombre"] for s in resp.json()]
    assert "Test List" in names


# ─── GET by ID ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_sucursal_by_id(client: AsyncClient):
    headers = _admin_headers()
    create_resp = await client.post(
        BASE, json={"nombre": "Detalle"}, headers=headers
    )
    suc_id = create_resp.json()["id"]
    resp = await client.get(f"{BASE}/{suc_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == suc_id


@pytest.mark.asyncio
async def test_get_sucursal_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"{BASE}/{fake_id}", headers=_admin_headers())
    assert resp.status_code == 404


# ─── UPDATE ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_sucursal(client: AsyncClient):
    headers = _admin_headers()
    create_resp = await client.post(
        BASE, json={"nombre": "Original"}, headers=headers
    )
    suc_id = create_resp.json()["id"]

    resp = await client.patch(
        f"{BASE}/{suc_id}",
        json={"nombre": "Renombrada", "telefono": "+56912345678"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Renombrada"
    assert resp.json()["telefono"] == "+56912345678"


# ─── DEACTIVATE ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_deactivate_sucursal(client: AsyncClient):
    headers = _admin_headers()
    create_resp = await client.post(
        BASE, json={"nombre": "Para Borrar"}, headers=headers
    )
    suc_id = create_resp.json()["id"]

    resp = await client.delete(f"{BASE}/{suc_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["activo"] is False


@pytest.mark.asyncio
async def test_deactivate_principal_blocked_when_others_exist(client: AsyncClient):
    """Cannot deactivate principal if other active sucursales exist."""
    from app.models.tenant import Tenant
    from sqlalchemy import select

    # Upgrade to PRO
    async with TestSessionFactory() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(TENANT_ID))
        )
        tenant = result.scalar_one()
        tenant.plan = "PRO"
        await session.commit()

    headers = _admin_headers()
    resp1 = await client.post(BASE, json={"nombre": "Principal Test"}, headers=headers)
    assert resp1.status_code == 201
    principal_id = resp1.json()["id"]

    resp2 = await client.post(BASE, json={"nombre": "Otra Test"}, headers=headers)
    assert resp2.status_code == 201

    # Try to deactivate principal — should fail
    resp = await client.delete(f"{BASE}/{principal_id}", headers=headers)
    assert resp.status_code == 409


# ─── AUTH ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_requires_auth(client: AsyncClient):
    resp = await client.get(BASE)
    assert resp.status_code in (401, 403)


# ─── TENANT ISOLATION ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tenant_isolation(client: AsyncClient):
    """Sucursales from tenant A not visible to tenant B."""
    headers_a = _admin_headers()
    await client.post(BASE, json={"nombre": "Tenant A Branch"}, headers=headers_a)

    other_tenant = str(uuid.uuid4())
    headers_b = _admin_headers(tenant_id=other_tenant)
    resp = await client.get(BASE, headers=headers_b)
    assert resp.status_code == 200
    names = [s["nombre"] for s in resp.json()]
    assert "Tenant A Branch" not in names


# ─── SLUG GENERATION ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_slug_is_generated(client: AsyncClient):
    headers = _admin_headers()
    resp = await client.post(
        BASE, json={"nombre": "Mi Restaurante #1"}, headers=headers
    )
    assert resp.status_code == 201
    slug = resp.json()["slug"]
    assert "mi-restaurante-1" in slug
    assert len(slug) > len("mi-restaurante-1")  # has uuid suffix


# ─── LOCATION FIELDS ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_sucursal_with_location_fields(client: AsyncClient):
    """Sucursal can be created with full location fields."""
    headers = _admin_headers()
    resp = await client.post(
        BASE,
        json={
            "nombre": "Con Ubicacion",
            "direccion": "Av. Libertador 1234",
            "ciudad": "Santiago",
            "region": "Region Metropolitana",
            "codigo_postal": "8320000",
            "pais": "CL",
            "google_maps_url": "https://maps.google.com/?q=Santiago",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ciudad"] == "Santiago"
    assert data["region"] == "Region Metropolitana"
    assert data["codigo_postal"] == "8320000"
    assert data["pais"] == "CL"
    assert data["google_maps_url"] == "https://maps.google.com/?q=Santiago"


@pytest.mark.asyncio
async def test_update_sucursal_location_fields(client: AsyncClient):
    """Location fields can be updated via PATCH."""
    headers = _admin_headers()
    create_resp = await client.post(
        BASE, json={"nombre": "Sin Ubicacion"}, headers=headers
    )
    suc_id = create_resp.json()["id"]

    resp = await client.patch(
        f"{BASE}/{suc_id}",
        json={"ciudad": "Lima", "pais": "PE"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ciudad"] == "Lima"
    assert resp.json()["pais"] == "PE"


@pytest.mark.asyncio
async def test_default_pais_is_cl(client: AsyncClient):
    """Default pais should be CL when not specified."""
    headers = _admin_headers()
    resp = await client.post(
        BASE, json={"nombre": "Default Pais"}, headers=headers
    )
    assert resp.status_code == 201
    assert resp.json()["pais"] == "CL"


# ─── BRANCH ACCESS ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_branch_admin_cannot_update_other_branch(client: AsyncClient):
    """ADMIN scoped to branch A cannot PATCH branch B."""
    headers_global = _admin_headers()
    create_resp = await client.post(
        BASE, json={"nombre": "Branch B"}, headers=headers_global
    )
    branch_b_id = create_resp.json()["id"]

    branch_a_id = str(uuid.uuid4())
    token = make_token(tenant_id=TENANT_ID, role="ADMIN", sucursal_id=branch_a_id)
    headers_branch_a = {"Authorization": f"Bearer {token}", "X-Tenant-ID": TENANT_ID}

    resp = await client.patch(
        f"{BASE}/{branch_b_id}",
        json={"nombre": "Hacked"},
        headers=headers_branch_a,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_global_admin_can_update_any_branch(client: AsyncClient):
    """ADMIN with sucursal_id=None can PATCH any branch."""
    headers = _admin_headers()
    create_resp = await client.post(
        BASE, json={"nombre": "Any Branch"}, headers=headers
    )
    suc_id = create_resp.json()["id"]

    resp = await client.patch(
        f"{BASE}/{suc_id}",
        json={"nombre": "Updated by Global"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Updated by Global"
