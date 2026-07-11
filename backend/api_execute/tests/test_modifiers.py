"""Tests for modifiers: modifier groups CRUD, modifiers CRUD, product assignment, auth."""

import uuid

import pytest

from .conftest import TENANT_ID, make_token

BASE = "/api/v1/core/modifier-groups"


# ---------------------------------------------------------------------------
# Helper: create a modifier group via the API, return response JSON
# ---------------------------------------------------------------------------
async def _create_group(client, auth_headers, *, nombre="Tamaño", tipo="SINGLE_SELECT", **kwargs):
    payload = {"nombre": nombre, "tipo": tipo, **kwargs}
    resp = await client.post(BASE, json=payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_producto(client, auth_headers, *, nombre="Hamburguesa", precio="8500.00"):
    resp = await client.post("/api/v1/core/productos", json={
        "nombre": nombre,
        "precio": precio,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════════
# 1. Create modifier group
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_modifier_group_minimal(client, auth_headers):
    """Create a modifier group with only required fields."""
    data = await _create_group(client, auth_headers)
    assert data["nombre"] == "Tamaño"
    assert data["tipo"] == "SINGLE_SELECT"
    assert data["obligatorio"] is False
    assert data["max_selecciones"] is None
    assert data["activo"] is True
    assert data["tenant_id"] == TENANT_ID
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_modifier_group_all_fields(client, auth_headers):
    """Create a modifier group with all optional fields."""
    data = await _create_group(
        client, auth_headers,
        nombre="Extras",
        tipo="MULTI_SELECT",
        obligatorio=True,
        max_selecciones=3,
    )
    assert data["nombre"] == "Extras"
    assert data["tipo"] == "MULTI_SELECT"
    assert data["obligatorio"] is True
    assert data["max_selecciones"] == 3


@pytest.mark.asyncio
async def test_create_modifier_group_with_inline_modifiers(client, auth_headers):
    """Create a group with inline modifiers in a single request."""
    resp = await client.post(BASE, json={
        "nombre": "Término Carne",
        "tipo": "SINGLE_SELECT",
        "obligatorio": True,
        "modifiers": [
            {"nombre": "Término Medio", "precio_delta": "0", "orden": 0},
            {"nombre": "Tres Cuartos", "precio_delta": "0", "orden": 1},
            {"nombre": "Bien Cocido", "precio_delta": "0", "orden": 2},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Término Carne"
    assert len(data["modifiers"]) == 3
    modifier_names = [m["nombre"] for m in data["modifiers"]]
    assert "Término Medio" in modifier_names
    assert "Tres Cuartos" in modifier_names
    assert "Bien Cocido" in modifier_names


@pytest.mark.asyncio
async def test_create_modifier_group_with_inline_modifiers_precio_delta(client, auth_headers):
    """Inline modifiers with precio_delta are stored correctly."""
    resp = await client.post(BASE, json={
        "nombre": "Tamaño Bebida",
        "tipo": "SINGLE_SELECT",
        "modifiers": [
            {"nombre": "Regular", "precio_delta": "0"},
            {"nombre": "Grande", "precio_delta": "500"},
            {"nombre": "XL", "precio_delta": "1000"},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    mods = {m["nombre"]: m for m in data["modifiers"]}
    assert float(mods["Regular"]["precio_delta"]) == 0
    assert float(mods["Grande"]["precio_delta"]) == 500
    assert float(mods["XL"]["precio_delta"]) == 1000


@pytest.mark.asyncio
async def test_create_modifier_group_invalid_tipo(client, auth_headers):
    """Invalid tipo value should return 422."""
    resp = await client.post(BASE, json={
        "nombre": "Bad Type",
        "tipo": "INVALID_TYPE",
    }, headers=auth_headers)
    assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# 2. List modifier groups (paginated)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_modifier_groups(client, auth_headers):
    """List returns paginated response with at least the created group."""
    await _create_group(client, auth_headers, nombre="ListTest1")
    await _create_group(client, auth_headers, nombre="ListTest2")

    resp = await client.get(BASE, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "meta" in data
    assert data["meta"]["total"] >= 2


@pytest.mark.asyncio
async def test_list_modifier_groups_filter_nombre(client, auth_headers):
    """Filter by nombre partial match."""
    await _create_group(client, auth_headers, nombre="Salsa Picante")
    await _create_group(client, auth_headers, nombre="Salsa Dulce")
    await _create_group(client, auth_headers, nombre="Unrelated Group")

    resp = await client.get(f"{BASE}?nombre=Salsa", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["total"] >= 2
    for item in data["data"]:
        assert "Salsa" in item["nombre"] or "salsa" in item["nombre"].lower()


@pytest.mark.asyncio
async def test_list_modifier_groups_pagination(client, auth_headers):
    """Pagination params limit and offset work."""
    for i in range(5):
        await _create_group(client, auth_headers, nombre=f"Page{i}")

    resp = await client.get(f"{BASE}?page=1&page_size=2", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) <= 2
    assert data["meta"]["page_size"] == 2


# ═══════════════════════════════════════════════════════════════════════════
# 3. Get single modifier group
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_modifier_group(client, auth_headers):
    """Get a single modifier group by ID."""
    created = await _create_group(client, auth_headers, nombre="GetSingle")
    group_id = created["id"]

    resp = await client.get(f"{BASE}/{group_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == group_id
    assert data["nombre"] == "GetSingle"


@pytest.mark.asyncio
async def test_get_modifier_group_not_found(client, auth_headers):
    """Get with nonexistent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"{BASE}/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_modifier_group_includes_modifiers(client, auth_headers):
    """Get group response includes its modifiers (eager loaded)."""
    resp = await client.post(BASE, json={
        "nombre": "Con Opciones",
        "tipo": "MULTI_SELECT",
        "modifiers": [
            {"nombre": "Opción A", "precio_delta": "100"},
            {"nombre": "Opción B", "precio_delta": "200"},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201
    group_id = resp.json()["id"]

    get_resp = await client.get(f"{BASE}/{group_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert len(data["modifiers"]) == 2


# ═══════════════════════════════════════════════════════════════════════════
# 4. Update modifier group
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_update_modifier_group_nombre(client, auth_headers):
    """PATCH updates only the specified fields."""
    created = await _create_group(client, auth_headers, nombre="OldGroupName")
    group_id = created["id"]

    resp = await client.patch(f"{BASE}/{group_id}", json={
        "nombre": "NewGroupName",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "NewGroupName"
    # Other fields remain unchanged
    assert resp.json()["tipo"] == "SINGLE_SELECT"


@pytest.mark.asyncio
async def test_update_modifier_group_tipo(client, auth_headers):
    """PATCH can change the tipo field."""
    created = await _create_group(client, auth_headers, tipo="SINGLE_SELECT")
    group_id = created["id"]

    resp = await client.patch(f"{BASE}/{group_id}", json={
        "tipo": "MULTI_SELECT",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["tipo"] == "MULTI_SELECT"


@pytest.mark.asyncio
async def test_update_modifier_group_obligatorio(client, auth_headers):
    """PATCH can toggle obligatorio field."""
    created = await _create_group(client, auth_headers, obligatorio=False)
    group_id = created["id"]

    resp = await client.patch(f"{BASE}/{group_id}", json={
        "obligatorio": True,
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["obligatorio"] is True


@pytest.mark.asyncio
async def test_update_modifier_group_max_selecciones(client, auth_headers):
    """PATCH can set max_selecciones."""
    created = await _create_group(client, auth_headers)
    group_id = created["id"]

    resp = await client.patch(f"{BASE}/{group_id}", json={
        "max_selecciones": 5,
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["max_selecciones"] == 5


@pytest.mark.asyncio
async def test_update_modifier_group_not_found(client, auth_headers):
    """PATCH with nonexistent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.patch(f"{BASE}/{fake_id}", json={
        "nombre": "Nope",
    }, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_modifier_group_invalid_tipo(client, auth_headers):
    """PATCH with invalid tipo returns 422."""
    created = await _create_group(client, auth_headers)
    group_id = created["id"]

    resp = await client.patch(f"{BASE}/{group_id}", json={
        "tipo": "BOGUS",
    }, headers=auth_headers)
    assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# 5. Soft-delete modifier group
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_soft_delete_modifier_group(client, auth_headers):
    """DELETE soft-deletes (204) and subsequent GET returns 404."""
    created = await _create_group(client, auth_headers, nombre="DeleteGroup")
    group_id = created["id"]

    resp = await client.delete(f"{BASE}/{group_id}", headers=auth_headers)
    assert resp.status_code == 204

    get_resp = await client.get(f"{BASE}/{group_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_soft_delete_modifier_group_not_found(client, auth_headers):
    """DELETE with nonexistent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"{BASE}/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_soft_deleted_group_excluded_from_list(client, auth_headers):
    """Soft-deleted groups do not appear in list results."""
    created = await _create_group(client, auth_headers, nombre="WillVanish")
    group_id = created["id"]

    await client.delete(f"{BASE}/{group_id}", headers=auth_headers)

    resp = await client.get(f"{BASE}?nombre=WillVanish", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    ids = [item["id"] for item in data["data"]]
    assert group_id not in ids


# ═══════════════════════════════════════════════════════════════════════════
# 6. Create modifier within group
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_modifier(client, auth_headers):
    """POST creates a modifier within an existing group."""
    group = await _create_group(client, auth_headers, nombre="Aderezos")
    group_id = group["id"]

    resp = await client.post(f"{BASE}/{group_id}/modifiers", json={
        "nombre": "Ketchup",
        "precio_delta": "0",
        "orden": 0,
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Ketchup"
    assert data["grupo_id"] == group_id
    assert data["activo"] is True
    assert float(data["precio_delta"]) == 0
    assert data["orden"] == 0


@pytest.mark.asyncio
async def test_create_modifier_with_precio_delta(client, auth_headers):
    """Modifier with nonzero precio_delta."""
    group = await _create_group(client, auth_headers, nombre="Agregados")
    group_id = group["id"]

    resp = await client.post(f"{BASE}/{group_id}/modifiers", json={
        "nombre": "Queso Extra",
        "precio_delta": "1500",
        "orden": 1,
    }, headers=auth_headers)
    assert resp.status_code == 201
    assert float(resp.json()["precio_delta"]) == 1500


@pytest.mark.asyncio
async def test_create_modifier_group_not_found(client, auth_headers):
    """Creating a modifier in a nonexistent group returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"{BASE}/{fake_id}/modifiers", json={
        "nombre": "Ghost",
        "precio_delta": "0",
        "orden": 0,
    }, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_modifiers_in_group(client, auth_headers):
    """GET /{group_id}/modifiers returns modifiers ordered by orden."""
    group = await _create_group(client, auth_headers, nombre="ListMods")
    group_id = group["id"]

    await client.post(f"{BASE}/{group_id}/modifiers", json={
        "nombre": "Mod B", "precio_delta": "0", "orden": 2,
    }, headers=auth_headers)
    await client.post(f"{BASE}/{group_id}/modifiers", json={
        "nombre": "Mod A", "precio_delta": "0", "orden": 1,
    }, headers=auth_headers)

    resp = await client.get(f"{BASE}/{group_id}/modifiers", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Should be ordered by orden
    assert data[0]["nombre"] == "Mod A"
    assert data[1]["nombre"] == "Mod B"


# ═══════════════════════════════════════════════════════════════════════════
# 7. Update modifier
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_update_modifier_nombre(client, auth_headers):
    """PATCH modifier updates nombre."""
    group = await _create_group(client, auth_headers, nombre="UpdModGroup")
    group_id = group["id"]

    create_resp = await client.post(f"{BASE}/{group_id}/modifiers", json={
        "nombre": "OldModName",
        "precio_delta": "0",
        "orden": 0,
    }, headers=auth_headers)
    mod_id = create_resp.json()["id"]

    resp = await client.patch(f"{BASE}/modifiers/{mod_id}", json={
        "nombre": "NewModName",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "NewModName"


@pytest.mark.asyncio
async def test_update_modifier_precio_delta(client, auth_headers):
    """PATCH modifier updates precio_delta."""
    group = await _create_group(client, auth_headers, nombre="PriceGroup")
    group_id = group["id"]

    create_resp = await client.post(f"{BASE}/{group_id}/modifiers", json={
        "nombre": "Topping",
        "precio_delta": "100",
        "orden": 0,
    }, headers=auth_headers)
    mod_id = create_resp.json()["id"]

    resp = await client.patch(f"{BASE}/modifiers/{mod_id}", json={
        "precio_delta": "250",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert float(resp.json()["precio_delta"]) == 250


@pytest.mark.asyncio
async def test_update_modifier_orden(client, auth_headers):
    """PATCH modifier updates orden."""
    group = await _create_group(client, auth_headers, nombre="OrdenGroup")
    group_id = group["id"]

    create_resp = await client.post(f"{BASE}/{group_id}/modifiers", json={
        "nombre": "Item",
        "precio_delta": "0",
        "orden": 0,
    }, headers=auth_headers)
    mod_id = create_resp.json()["id"]

    resp = await client.patch(f"{BASE}/modifiers/{mod_id}", json={
        "orden": 5,
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["orden"] == 5


@pytest.mark.asyncio
async def test_update_modifier_not_found(client, auth_headers):
    """PATCH with nonexistent modifier ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.patch(f"{BASE}/modifiers/{fake_id}", json={
        "nombre": "Nope",
    }, headers=auth_headers)
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# 8. Soft-delete modifier
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_soft_delete_modifier(client, auth_headers):
    """DELETE modifier returns 204."""
    group = await _create_group(client, auth_headers, nombre="DelModGroup")
    group_id = group["id"]

    create_resp = await client.post(f"{BASE}/{group_id}/modifiers", json={
        "nombre": "WillBeDeleted",
        "precio_delta": "0",
        "orden": 0,
    }, headers=auth_headers)
    mod_id = create_resp.json()["id"]

    resp = await client.delete(f"{BASE}/modifiers/{mod_id}", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_soft_delete_modifier_not_found(client, auth_headers):
    """DELETE with nonexistent modifier ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"{BASE}/modifiers/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_soft_deleted_modifier_excluded_from_list(client, auth_headers):
    """Soft-deleted modifiers do not appear in group's modifier list."""
    group = await _create_group(client, auth_headers, nombre="ExcludeModGroup")
    group_id = group["id"]

    create_resp = await client.post(f"{BASE}/{group_id}/modifiers", json={
        "nombre": "Visible",
        "precio_delta": "0",
        "orden": 0,
    }, headers=auth_headers)
    visible_id = create_resp.json()["id"]

    create_resp2 = await client.post(f"{BASE}/{group_id}/modifiers", json={
        "nombre": "Hidden",
        "precio_delta": "0",
        "orden": 1,
    }, headers=auth_headers)
    hidden_id = create_resp2.json()["id"]

    # Delete one
    await client.delete(f"{BASE}/modifiers/{hidden_id}", headers=auth_headers)

    # List should only contain the visible one
    resp = await client.get(f"{BASE}/{group_id}/modifiers", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    ids = [m["id"] for m in data]
    assert visible_id in ids
    assert hidden_id not in ids


# ═══════════════════════════════════════════════════════════════════════════
# 9. Assign modifier groups to product (replace semantics)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_assign_modifier_groups_to_product(client, auth_headers):
    """PATCH assigns modifier groups to a product (replaces existing)."""
    product = await _create_producto(client, auth_headers, nombre="Pizza Margherita")
    producto_id = product["id"]

    group1 = await _create_group(client, auth_headers, nombre="Masa")
    group2 = await _create_group(client, auth_headers, nombre="Toppings")

    resp = await client.patch(f"{BASE}/productos/{producto_id}", json={
        "modifier_group_ids": [group1["id"], group2["id"]],
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert group1["id"] in data
    assert group2["id"] in data


@pytest.mark.asyncio
async def test_assign_modifier_groups_replaces_existing(client, auth_headers):
    """Subsequent PATCH replaces all previous assignments."""
    product = await _create_producto(client, auth_headers, nombre="Burger Doble")
    producto_id = product["id"]

    group1 = await _create_group(client, auth_headers, nombre="Cocción")
    group2 = await _create_group(client, auth_headers, nombre="Pan")
    group3 = await _create_group(client, auth_headers, nombre="Salsas")

    # First assignment: group1 + group2
    await client.patch(f"{BASE}/productos/{producto_id}", json={
        "modifier_group_ids": [group1["id"], group2["id"]],
    }, headers=auth_headers)

    # Second assignment: only group3 (replaces)
    resp = await client.patch(f"{BASE}/productos/{producto_id}", json={
        "modifier_group_ids": [group3["id"]],
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert group3["id"] in data

    # Verify via GET
    get_resp = await client.get(f"{BASE}/productos/{producto_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assigned_ids = [g["id"] for g in get_data]
    assert group3["id"] in assigned_ids
    assert group1["id"] not in assigned_ids
    assert group2["id"] not in assigned_ids


@pytest.mark.asyncio
async def test_assign_empty_list_clears_assignments(client, auth_headers):
    """Assigning an empty list removes all modifier group assignments."""
    product = await _create_producto(client, auth_headers, nombre="Empanada")
    producto_id = product["id"]

    group = await _create_group(client, auth_headers, nombre="Relleno")
    await client.patch(f"{BASE}/productos/{producto_id}", json={
        "modifier_group_ids": [group["id"]],
    }, headers=auth_headers)

    # Clear assignments
    resp = await client.patch(f"{BASE}/productos/{producto_id}", json={
        "modifier_group_ids": [],
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    get_resp = await client.get(f"{BASE}/productos/{producto_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json() == []


@pytest.mark.asyncio
async def test_assign_modifier_groups_product_not_found(client, auth_headers):
    """Assigning to nonexistent product returns 404."""
    fake_id = str(uuid.uuid4())
    group = await _create_group(client, auth_headers, nombre="Orphan")

    resp = await client.patch(f"{BASE}/productos/{fake_id}", json={
        "modifier_group_ids": [group["id"]],
    }, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_assign_modifier_groups_group_not_found(client, auth_headers):
    """Assigning nonexistent modifier group ID returns 404."""
    product = await _create_producto(client, auth_headers, nombre="Sushi")
    producto_id = product["id"]
    fake_group_id = str(uuid.uuid4())

    resp = await client.patch(f"{BASE}/productos/{producto_id}", json={
        "modifier_group_ids": [fake_group_id],
    }, headers=auth_headers)
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# 10. Get product modifier groups
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_product_modifier_groups(client, auth_headers):
    """GET returns modifier groups assigned to a product."""
    product = await _create_producto(client, auth_headers, nombre="Tacos")
    producto_id = product["id"]

    group1 = await _create_group(client, auth_headers, nombre="Proteína")
    group2 = await _create_group(client, auth_headers, nombre="Guarnición")

    await client.patch(f"{BASE}/productos/{producto_id}", json={
        "modifier_group_ids": [group1["id"], group2["id"]],
    }, headers=auth_headers)

    resp = await client.get(f"{BASE}/productos/{producto_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assigned_ids = [g["id"] for g in data]
    assert group1["id"] in assigned_ids
    assert group2["id"] in assigned_ids


@pytest.mark.asyncio
async def test_get_product_modifier_groups_empty(client, auth_headers):
    """GET returns empty list when product has no modifier groups assigned."""
    product = await _create_producto(client, auth_headers, nombre="Agua")
    producto_id = product["id"]

    resp = await client.get(f"{BASE}/productos/{producto_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_product_modifier_groups_excludes_deleted_groups(client, auth_headers):
    """Soft-deleted modifier groups are excluded from product's group list."""
    product = await _create_producto(client, auth_headers, nombre="Nachos")
    producto_id = product["id"]

    group_active = await _create_group(client, auth_headers, nombre="Queso")
    group_deleted = await _create_group(client, auth_headers, nombre="Jalapeño")

    await client.patch(f"{BASE}/productos/{producto_id}", json={
        "modifier_group_ids": [group_active["id"], group_deleted["id"]],
    }, headers=auth_headers)

    # Soft-delete one group
    await client.delete(f"{BASE}/{group_deleted['id']}", headers=auth_headers)

    resp = await client.get(f"{BASE}/productos/{producto_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assigned_ids = [g["id"] for g in data]
    assert group_active["id"] in assigned_ids
    assert group_deleted["id"] not in assigned_ids


# ═══════════════════════════════════════════════════════════════════════════
# 11. Auth: require ADMIN/SUPERADMIN for writes, allow all roles for reads
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_modifier_group_requires_admin(client):
    """VIEWER role cannot create modifier groups."""
    viewer_token = make_token(role="VIEWER")
    viewer_headers = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-ID": TENANT_ID,
    }
    resp = await client.post(BASE, json={
        "nombre": "Forbidden",
        "tipo": "SINGLE_SELECT",
    }, headers=viewer_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_modifier_group_requires_admin(client, auth_headers):
    """VIEWER role cannot update modifier groups."""
    created = await _create_group(client, auth_headers, nombre="ProtectedUpdate")
    group_id = created["id"]

    viewer_token = make_token(role="VIEWER")
    viewer_headers = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-ID": TENANT_ID,
    }
    resp = await client.patch(f"{BASE}/{group_id}", json={
        "nombre": "Hacked",
    }, headers=viewer_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_modifier_group_requires_admin(client, auth_headers):
    """VIEWER role cannot delete modifier groups."""
    created = await _create_group(client, auth_headers, nombre="ProtectedDel")
    group_id = created["id"]

    viewer_token = make_token(role="VIEWER")
    viewer_headers = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-ID": TENANT_ID,
    }
    resp = await client.delete(f"{BASE}/{group_id}", headers=viewer_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_modifier_requires_admin(client, auth_headers):
    """VIEWER role cannot create modifiers."""
    group = await _create_group(client, auth_headers, nombre="ProtectedModCreate")
    group_id = group["id"]

    viewer_token = make_token(role="VIEWER")
    viewer_headers = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-ID": TENANT_ID,
    }
    resp = await client.post(f"{BASE}/{group_id}/modifiers", json={
        "nombre": "Blocked",
        "precio_delta": "0",
        "orden": 0,
    }, headers=viewer_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_modifier_requires_admin(client, auth_headers):
    """VIEWER role cannot update modifiers."""
    group = await _create_group(client, auth_headers, nombre="ProtModUpd")
    group_id = group["id"]

    create_resp = await client.post(f"{BASE}/{group_id}/modifiers", json={
        "nombre": "Locked",
        "precio_delta": "0",
        "orden": 0,
    }, headers=auth_headers)
    mod_id = create_resp.json()["id"]

    viewer_token = make_token(role="VIEWER")
    viewer_headers = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-ID": TENANT_ID,
    }
    resp = await client.patch(f"{BASE}/modifiers/{mod_id}", json={
        "nombre": "Hacked",
    }, headers=viewer_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_modifier_requires_admin(client, auth_headers):
    """VIEWER role cannot delete modifiers."""
    group = await _create_group(client, auth_headers, nombre="ProtModDel")
    group_id = group["id"]

    create_resp = await client.post(f"{BASE}/{group_id}/modifiers", json={
        "nombre": "NoDel",
        "precio_delta": "0",
        "orden": 0,
    }, headers=auth_headers)
    mod_id = create_resp.json()["id"]

    viewer_token = make_token(role="VIEWER")
    viewer_headers = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-ID": TENANT_ID,
    }
    resp = await client.delete(f"{BASE}/modifiers/{mod_id}", headers=viewer_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_assign_product_modifier_groups_requires_admin(client, auth_headers):
    """VIEWER role cannot assign modifier groups to products."""
    product = await _create_producto(client, auth_headers, nombre="Protected Pizza")
    producto_id = product["id"]

    group = await _create_group(client, auth_headers, nombre="ProtAssign")

    viewer_token = make_token(role="VIEWER")
    viewer_headers = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-ID": TENANT_ID,
    }
    resp = await client.patch(f"{BASE}/productos/{producto_id}", json={
        "modifier_group_ids": [group["id"]],
    }, headers=viewer_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_read_modifier_groups_allowed_for_all_roles(client, auth_headers):
    """All authenticated roles can read modifier groups."""
    await _create_group(client, auth_headers, nombre="ReadableGroup")

    for role in ("ADMIN", "SUPERADMIN", "PERSONAL", "ASESOR", "VIEWER"):
        token = make_token(role=role)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": TENANT_ID,
        }
        resp = await client.get(BASE, headers=headers)
        assert resp.status_code == 200, f"Role {role} should be able to read modifier groups"


@pytest.mark.asyncio
async def test_read_product_modifier_groups_allowed_for_all_roles(client, auth_headers):
    """All authenticated roles can read product modifier groups."""
    product = await _create_producto(client, auth_headers, nombre="ReadableProd")
    producto_id = product["id"]

    for role in ("ADMIN", "SUPERADMIN", "PERSONAL", "ASESOR", "VIEWER"):
        token = make_token(role=role)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": TENANT_ID,
        }
        resp = await client.get(f"{BASE}/productos/{producto_id}", headers=headers)
        assert resp.status_code == 200, f"Role {role} should be able to read product modifier groups"


@pytest.mark.asyncio
async def test_no_auth_returns_401(client):
    """Requests without auth token return 401."""
    resp = await client.get(BASE)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_superadmin_can_write(client):
    """SUPERADMIN role can create modifier groups."""
    token = make_token(role="SUPERADMIN")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
    }
    resp = await client.post(BASE, json={
        "nombre": "SuperAdminGroup",
        "tipo": "MULTI_SELECT",
    }, headers=headers)
    assert resp.status_code == 201
