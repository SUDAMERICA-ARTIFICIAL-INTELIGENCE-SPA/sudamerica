"""Tests for comandas: CRUD, FSM transitions, KDS view, auth, pricing."""

import pytest

from .conftest import TENANT_ID, make_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_producto(client, auth_headers, nombre="Hamburguesa", precio="8500.00"):
    """Create a producto and return its response dict."""
    resp = await client.post("/api/v1/core/productos", json={
        "nombre": nombre,
        "precio": precio,
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_modifier_group_with_modifier(
    client, auth_headers,
    group_name="Extras", modifier_name="Queso extra", precio_delta="500.00",
):
    """Create a modifier group with one inline modifier and return (group, modifier_id)."""
    resp = await client.post("/api/v1/core/modifier-groups", json={
        "nombre": group_name,
        "tipo": "SINGLE_SELECT",
        "modifiers": [
            {"nombre": modifier_name, "precio_delta": precio_delta, "orden": 0},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    group = resp.json()
    modifier_id = group["modifiers"][0]["id"]
    return group, modifier_id


async def _create_comanda(
    client, auth_headers, producto_id,
    tipo_entrega="MESA", canal_origen="PRESENCIAL",
    cantidad=1, numero_mesa=5, notas=None,
    modifiers_json=None, prioridad=0,
):
    """Create a comanda with one item and return its response dict."""
    item = {
        "producto_id": producto_id,
        "cantidad": cantidad,
    }
    if modifiers_json is not None:
        item["modifiers_json"] = modifiers_json
    if notas:
        item["notas"] = notas

    body = {
        "tipo_entrega": tipo_entrega,
        "canal_origen": canal_origen,
        "numero_mesa": numero_mesa,
        "prioridad": prioridad,
        "items": [item],
    }
    if notas:
        body["notas"] = notas
    resp = await client.post("/api/v1/core/comandas", json=body, headers=auth_headers)
    return resp


async def _transition_estado(client, auth_headers, comanda_id, estado):
    """Transition comanda estado and return response."""
    return await client.patch(
        f"/api/v1/core/comandas/{comanda_id}/estado",
        json={"estado": estado},
        headers=auth_headers,
    )


# ---------------------------------------------------------------------------
# 1. Create comanda with items (basic)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_comanda_basic(client, auth_headers):
    """POST /comandas with one item returns 201 and correct structure."""
    prod = await _create_producto(client, auth_headers)

    resp = await _create_comanda(client, auth_headers, prod["id"])
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["tipo_entrega"] == "MESA"
    assert data["canal_origen"] == "PRESENCIAL"
    assert data["numero_mesa"] == 5
    assert data["estado"] == "PENDIENTE"
    assert data["activo"] is True
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["producto_id"] == prod["id"]
    assert item["cantidad"] == 1
    assert float(item["precio_unitario"]) == 8500.0
    assert float(item["subtotal"]) == 8500.0
    assert item["producto_nombre"] == "Hamburguesa"


# ---------------------------------------------------------------------------
# 2. Create comanda validates at least 1 item
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_comanda_no_items_raises_error(client, auth_headers):
    """POST /comandas with empty items list should raise ValueError."""
    body = {
        "tipo_entrega": "MESA",
        "canal_origen": "PRESENCIAL",
        "numero_mesa": 1,
        "items": [],
    }
    with pytest.raises(ValueError, match="at least one item"):
        await client.post("/api/v1/core/comandas", json=body, headers=auth_headers)


# ---------------------------------------------------------------------------
# 3. List comandas (paginated, with filters)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_comandas_paginated(client, auth_headers):
    """GET /comandas returns paginated results."""
    prod = await _create_producto(client, auth_headers, "Ensalada", "4500.00")
    await _create_comanda(client, auth_headers, prod["id"])
    await _create_comanda(client, auth_headers, prod["id"], tipo_entrega="DELIVERY", numero_mesa=None)

    resp = await client.get("/api/v1/core/comandas", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["total"] >= 2
    assert len(data["data"]) >= 2


@pytest.mark.asyncio
async def test_list_comandas_filter_by_estado(client, auth_headers):
    """GET /comandas?estado=PENDIENTE returns only PENDIENTE comandas."""
    prod = await _create_producto(client, auth_headers, "Pasta", "6000.00")
    resp = await _create_comanda(client, auth_headers, prod["id"])
    assert resp.status_code == 201

    # Transition one to EN_COCINA
    comanda_id = resp.json()["id"]
    await _transition_estado(client, auth_headers, comanda_id, "EN_COCINA")

    # Filter by EN_COCINA
    list_resp = await client.get(
        "/api/v1/core/comandas?estado=EN_COCINA", headers=auth_headers
    )
    assert list_resp.status_code == 200
    for c in list_resp.json()["data"]:
        assert c["estado"] == "EN_COCINA"


@pytest.mark.asyncio
async def test_list_comandas_filter_by_tipo_entrega(client, auth_headers):
    """GET /comandas?tipo_entrega=RETIRO returns only RETIRO comandas."""
    prod = await _create_producto(client, auth_headers, "Sushi", "12000.00")
    await _create_comanda(client, auth_headers, prod["id"], tipo_entrega="RETIRO", numero_mesa=None)

    list_resp = await client.get(
        "/api/v1/core/comandas?tipo_entrega=RETIRO", headers=auth_headers
    )
    assert list_resp.status_code == 200
    for c in list_resp.json()["data"]:
        assert c["tipo_entrega"] == "RETIRO"


@pytest.mark.asyncio
async def test_list_comandas_filter_by_fecha_desde(client, auth_headers):
    """Regression: ``fecha_desde`` combined with other filters must not raise
    ``sqlalchemy.exc.ArgumentError``. Caused a prod 500 on 2026-04-14 when the
    KDS polled ``/comandas?estado=ENTREGADO&fecha_desde=...``.
    """
    prod = await _create_producto(client, auth_headers, "Pizza", "9000.00")
    await _create_comanda(client, auth_headers, prod["id"])

    resp = await client.get(
        "/api/v1/core/comandas",
        params={
            "estado": "ENTREGADO",
            "fecha_desde": "2026-04-13T00:00:00Z",
            "page_size": 50,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# 4. Get single comanda
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_comanda_by_id(client, auth_headers):
    """GET /comandas/{id} returns the specific comanda."""
    prod = await _create_producto(client, auth_headers, "Taco", "3500.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    assert create_resp.status_code == 201
    comanda_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/core/comandas/{comanda_id}", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == comanda_id
    assert data["tipo_entrega"] == "MESA"
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_get_comanda_not_found(client, auth_headers):
    """GET /comandas/{invalid-id} returns 404."""
    import uuid
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/core/comandas/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5. FSM transition: PENDIENTE â†’ EN_COCINA â†’ LISTO â†’ ENTREGADO
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fsm_full_happy_path(client, auth_headers):
    """Full FSM: PENDIENTE â†’ EN_COCINA â†’ LISTO â†’ ENTREGADO."""
    prod = await _create_producto(client, auth_headers, "Pizza", "9500.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    # PENDIENTE â†’ EN_COCINA
    resp1 = await _transition_estado(client, auth_headers, comanda_id, "EN_COCINA")
    assert resp1.status_code == 200
    assert resp1.json()["estado"] == "EN_COCINA"

    # EN_COCINA â†’ LISTO
    resp2 = await _transition_estado(client, auth_headers, comanda_id, "LISTO")
    assert resp2.status_code == 200
    assert resp2.json()["estado"] == "LISTO"

    # LISTO â†’ ENTREGADO
    resp3 = await _transition_estado(client, auth_headers, comanda_id, "ENTREGADO")
    assert resp3.status_code == 200
    assert resp3.json()["estado"] == "ENTREGADO"
    assert resp3.json()["entregado_at"] is not None


@pytest.mark.asyncio
async def test_entregado_creates_ventas_for_each_item(client, auth_headers):
    """ENTREGADO should persist ventas so metrics reflect delivered orders."""
    prod1 = await _create_producto(client, auth_headers, "Pizza Familiar", "9500.00")
    prod2 = await _create_producto(client, auth_headers, "Bebida", "2500.00")

    resp = await client.post(
        "/api/v1/core/comandas",
        json={
            "tipo_entrega": "MESA",
            "canal_origen": "PRESENCIAL",
            "numero_mesa": 3,
            "items": [
                {"producto_id": prod1["id"], "cantidad": 1},
                {"producto_id": prod2["id"], "cantidad": 2},
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    comanda_id = resp.json()["id"]

    await _transition_estado(client, auth_headers, comanda_id, "EN_COCINA")
    await _transition_estado(client, auth_headers, comanda_id, "LISTO")
    delivered = await _transition_estado(client, auth_headers, comanda_id, "ENTREGADO")
    assert delivered.status_code == 200
    assert delivered.json()["venta_id"] is not None

    ventas_resp = await client.get("/api/v1/core/ventas", headers=auth_headers)
    assert ventas_resp.status_code == 200
    ventas = [
        venta for venta in ventas_resp.json()["data"]
        if venta.get("notas") and f"COMANDA:{comanda_id}" in venta["notas"]
    ]

    assert len(ventas) == 2
    assert sum(float(venta["total"]) for venta in ventas) == pytest.approx(14500.0)


@pytest.mark.asyncio
async def test_fsm_pendiente_to_cancelado(client, auth_headers):
    """PENDIENTE â†’ CANCELADO should succeed."""
    prod = await _create_producto(client, auth_headers, "Burrito", "5000.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    resp = await _transition_estado(client, auth_headers, comanda_id, "CANCELADO")
    assert resp.status_code == 200
    assert resp.json()["estado"] == "CANCELADO"


# ---------------------------------------------------------------------------
# 6. FSM rejects invalid transitions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fsm_rejects_listo_to_pendiente(client, auth_headers):
    """LISTO â†’ PENDIENTE is not allowed, should return 422."""
    prod = await _create_producto(client, auth_headers, "Quesadilla", "4000.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    # Advance to LISTO
    await _transition_estado(client, auth_headers, comanda_id, "EN_COCINA")
    await _transition_estado(client, auth_headers, comanda_id, "LISTO")

    # Attempt invalid: LISTO â†’ PENDIENTE
    resp = await _transition_estado(client, auth_headers, comanda_id, "PENDIENTE")
    assert resp.status_code == 422
    assert "INVALID_TRANSITION" in resp.text


@pytest.mark.asyncio
async def test_fsm_rejects_entregado_to_en_cocina(client, auth_headers):
    """ENTREGADO is a terminal state â€” cannot transition anywhere."""
    prod = await _create_producto(client, auth_headers, "Empanada", "2500.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    # Advance to ENTREGADO
    await _transition_estado(client, auth_headers, comanda_id, "EN_COCINA")
    await _transition_estado(client, auth_headers, comanda_id, "LISTO")
    await _transition_estado(client, auth_headers, comanda_id, "ENTREGADO")

    # Attempt: ENTREGADO â†’ EN_COCINA
    resp = await _transition_estado(client, auth_headers, comanda_id, "EN_COCINA")
    assert resp.status_code == 422
    assert "INVALID_TRANSITION" in resp.text


@pytest.mark.asyncio
async def test_fsm_rejects_cancelado_to_listo(client, auth_headers):
    """CANCELADO is a terminal state â€” cannot transition anywhere."""
    prod = await _create_producto(client, auth_headers, "Arepa", "3000.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    await _transition_estado(client, auth_headers, comanda_id, "CANCELADO")

    resp = await _transition_estado(client, auth_headers, comanda_id, "LISTO")
    assert resp.status_code == 422
    assert "INVALID_TRANSITION" in resp.text


@pytest.mark.asyncio
async def test_fsm_rejects_pendiente_to_listo_skip(client, auth_headers):
    """PENDIENTE â†’ LISTO is not allowed (must go via EN_COCINA)."""
    prod = await _create_producto(client, auth_headers, "Ceviche", "7000.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    resp = await _transition_estado(client, auth_headers, comanda_id, "LISTO")
    assert resp.status_code == 422
    assert "INVALID_TRANSITION" in resp.text


# ---------------------------------------------------------------------------
# 7. KDS view (grouped by estado)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kds_view_grouped(client, auth_headers):
    """GET /comandas/kds returns dict with PENDIENTE, EN_COCINA, LISTO keys."""
    prod = await _create_producto(client, auth_headers, "Lomo Saltado", "11000.00")

    # Create 3 comandas in different states
    c1 = await _create_comanda(client, auth_headers, prod["id"])
    c2 = await _create_comanda(client, auth_headers, prod["id"])
    c3 = await _create_comanda(client, auth_headers, prod["id"])

    # c2 â†’ EN_COCINA
    await _transition_estado(client, auth_headers, c2.json()["id"], "EN_COCINA")
    # c3 â†’ EN_COCINA â†’ LISTO
    await _transition_estado(client, auth_headers, c3.json()["id"], "EN_COCINA")
    await _transition_estado(client, auth_headers, c3.json()["id"], "LISTO")

    resp = await client.get("/api/v1/core/comandas/kds", headers=auth_headers)
    assert resp.status_code == 200
    kds = resp.json()

    assert "PENDIENTE" in kds
    assert "EN_COCINA" in kds
    assert "LISTO" in kds

    # Verify the comandas are in their correct groups
    pendiente_ids = [c["id"] for c in kds["PENDIENTE"]]
    en_cocina_ids = [c["id"] for c in kds["EN_COCINA"]]
    listo_ids = [c["id"] for c in kds["LISTO"]]

    assert c1.json()["id"] in pendiente_ids
    assert c2.json()["id"] in en_cocina_ids
    assert c3.json()["id"] in listo_ids


@pytest.mark.asyncio
async def test_kds_excludes_entregado(client, auth_headers):
    """ENTREGADO comandas should NOT appear in KDS view."""
    prod = await _create_producto(client, auth_headers, "Pollo Asado", "7500.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    # Advance to ENTREGADO
    await _transition_estado(client, auth_headers, comanda_id, "EN_COCINA")
    await _transition_estado(client, auth_headers, comanda_id, "LISTO")
    await _transition_estado(client, auth_headers, comanda_id, "ENTREGADO")

    resp = await client.get("/api/v1/core/comandas/kds", headers=auth_headers)
    assert resp.status_code == 200
    kds = resp.json()

    all_kds_ids = (
        [c["id"] for c in kds["PENDIENTE"]]
        + [c["id"] for c in kds["EN_COCINA"]]
        + [c["id"] for c in kds["LISTO"]]
    )
    assert comanda_id not in all_kds_ids


# ---------------------------------------------------------------------------
# 8. Soft-delete comanda
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_soft_delete_comanda(client, auth_headers):
    """DELETE /comandas/{id} soft-deletes (returns 204), then GET returns 404."""
    prod = await _create_producto(client, auth_headers, "Nachos", "3800.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    # Delete
    del_resp = await client.delete(
        f"/api/v1/core/comandas/{comanda_id}", headers=auth_headers
    )
    assert del_resp.status_code == 204

    # Confirm gone
    get_resp = await client.get(
        f"/api/v1/core/comandas/{comanda_id}", headers=auth_headers
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_soft_delete_excludes_from_list(client, auth_headers):
    """Deleted comanda should not appear in list or KDS."""
    prod = await _create_producto(client, auth_headers, "Flan", "2000.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    await client.delete(
        f"/api/v1/core/comandas/{comanda_id}", headers=auth_headers
    )

    # Should not appear in KDS
    kds_resp = await client.get("/api/v1/core/comandas/kds", headers=auth_headers)
    all_kds_ids = []
    for estado_list in kds_resp.json().values():
        all_kds_ids.extend(c["id"] for c in estado_list)
    assert comanda_id not in all_kds_ids


# ---------------------------------------------------------------------------
# 9. Create comanda computes precio from producto + modifiers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_comanda_computes_price_from_producto(client, auth_headers):
    """Item precio_unitario should match product price when no modifiers."""
    prod = await _create_producto(client, auth_headers, "Risotto", "9800.00")

    resp = await _create_comanda(client, auth_headers, prod["id"], cantidad=3)
    assert resp.status_code == 201
    item = resp.json()["items"][0]

    assert float(item["precio_unitario"]) == 9800.0
    assert float(item["subtotal"]) == 9800.0 * 3


@pytest.mark.asyncio
async def test_create_comanda_with_modifiers_adds_precio_delta(client, auth_headers):
    """precio_unitario = product.precio + sum(modifier.precio_delta)."""
    prod = await _create_producto(client, auth_headers, "Burger Clasica", "7000.00")
    _group, modifier_id = await _create_modifier_group_with_modifier(
        client, auth_headers,
        group_name="Adicionales",
        modifier_name="Doble Queso",
        precio_delta="1500.00",
    )

    resp = await _create_comanda(
        client, auth_headers, prod["id"],
        cantidad=2,
        modifiers_json=[{"modifier_id": modifier_id}],
    )
    assert resp.status_code == 201
    item = resp.json()["items"][0]

    # 7000 + 1500 = 8500
    assert float(item["precio_unitario"]) == 8500.0
    # 8500 * 2 = 17000
    assert float(item["subtotal"]) == 17000.0


@pytest.mark.asyncio
async def test_create_comanda_with_multiple_modifiers(client, auth_headers):
    """Multiple modifiers should all add to precio_unitario."""
    prod = await _create_producto(client, auth_headers, "Hot Dog", "3000.00")

    # Create two modifier groups with different modifiers
    _g1, mod1_id = await _create_modifier_group_with_modifier(
        client, auth_headers,
        group_name="Salsas",
        modifier_name="Mostaza",
        precio_delta="200.00",
    )
    _g2, mod2_id = await _create_modifier_group_with_modifier(
        client, auth_headers,
        group_name="Toppings",
        modifier_name="Chucrut",
        precio_delta="800.00",
    )

    resp = await _create_comanda(
        client, auth_headers, prod["id"],
        cantidad=1,
        modifiers_json=[
            {"modifier_id": mod1_id},
            {"modifier_id": mod2_id},
        ],
    )
    assert resp.status_code == 201
    item = resp.json()["items"][0]

    # 3000 + 200 + 800 = 4000
    assert float(item["precio_unitario"]) == 4000.0
    assert float(item["subtotal"]) == 4000.0

    # Verify modifiers snapshot is stored
    assert len(item["modifiers_json"]) == 2
    modifier_names = {m["nombre"] for m in item["modifiers_json"]}
    assert "Mostaza" in modifier_names
    assert "Chucrut" in modifier_names


# ---------------------------------------------------------------------------
# 10. Auth: require ADMIN/ASESOR for writes, VIEWER can read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_viewer_can_read_comandas(client, auth_headers):
    """VIEWER role should be able to list and get comandas."""
    viewer_token = make_token(role="VIEWER")
    viewer_headers = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-ID": TENANT_ID,
    }

    # Create a comanda as ADMIN first
    prod = await _create_producto(client, auth_headers, "Limonada", "2000.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    # VIEWER can list
    list_resp = await client.get("/api/v1/core/comandas", headers=viewer_headers)
    assert list_resp.status_code == 200

    # VIEWER can get by id
    get_resp = await client.get(
        f"/api/v1/core/comandas/{comanda_id}", headers=viewer_headers
    )
    assert get_resp.status_code == 200

    # VIEWER can access KDS
    kds_resp = await client.get("/api/v1/core/comandas/kds", headers=viewer_headers)
    assert kds_resp.status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_create_comanda(client, auth_headers):
    """VIEWER role should NOT be able to create a comanda (403)."""
    viewer_token = make_token(role="VIEWER")
    viewer_headers = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-ID": TENANT_ID,
    }

    prod = await _create_producto(client, auth_headers, "Agua Mineral", "1000.00")
    resp = await _create_comanda(client, viewer_headers, prod["id"])
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_transition_estado(client, auth_headers):
    """VIEWER role should NOT be able to transition comanda estado (403)."""
    viewer_token = make_token(role="VIEWER")
    viewer_headers = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-ID": TENANT_ID,
    }

    prod = await _create_producto(client, auth_headers, "Cerveza", "3500.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    resp = await _transition_estado(client, viewer_headers, comanda_id, "EN_COCINA")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_comanda(client, auth_headers):
    """VIEWER role should NOT be able to delete a comanda (403).
    Note: DELETE requires AdminWriter (SUPERADMIN or ADMIN only)."""
    viewer_token = make_token(role="VIEWER")
    viewer_headers = {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-ID": TENANT_ID,
    }

    prod = await _create_producto(client, auth_headers, "Jugo Natural", "2500.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/core/comandas/{comanda_id}", headers=viewer_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_asesor_can_create_comanda(client, auth_headers, asesor_headers):
    """ASESOR role should be able to create a comanda (write access)."""
    prod = await _create_producto(client, auth_headers, "Cafe Latte", "2800.00")
    resp = await _create_comanda(client, asesor_headers, prod["id"])
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_asesor_can_transition_estado(client, auth_headers, asesor_headers):
    """ASESOR role should be able to transition comanda estado."""
    prod = await _create_producto(client, auth_headers, "Te Chai", "2200.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    resp = await _transition_estado(client, asesor_headers, comanda_id, "EN_COCINA")
    assert resp.status_code == 200
    assert resp.json()["estado"] == "EN_COCINA"


@pytest.mark.asyncio
async def test_asesor_cannot_delete_comanda(client, auth_headers, asesor_headers):
    """DELETE requires AdminWriter (ADMIN/SUPERADMIN), not ASESOR."""
    prod = await _create_producto(client, auth_headers, "Brownie", "3200.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/core/comandas/{comanda_id}", headers=asesor_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client):
    """Request without auth headers should be rejected."""
    resp = await client.get("/api/v1/core/comandas")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_comanda_multiple_items(client, auth_headers):
    """Comanda with multiple different items."""
    prod1 = await _create_producto(client, auth_headers, "Entrada Bruschetta", "4500.00")
    prod2 = await _create_producto(client, auth_headers, "Plato Salmon", "15000.00")

    body = {
        "tipo_entrega": "MESA",
        "canal_origen": "WEB",
        "numero_mesa": 12,
        "items": [
            {"producto_id": prod1["id"], "cantidad": 2},
            {"producto_id": prod2["id"], "cantidad": 1},
        ],
    }
    resp = await client.post("/api/v1/core/comandas", json=body, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["items"]) == 2

    # Verify each item's subtotal
    items_by_product = {i["producto_id"]: i for i in data["items"]}
    assert float(items_by_product[prod1["id"]]["subtotal"]) == 4500.0 * 2
    assert float(items_by_product[prod2["id"]]["subtotal"]) == 15000.0


@pytest.mark.asyncio
async def test_create_comanda_delivery_type(client, auth_headers):
    """Comanda with DELIVERY tipo_entrega."""
    prod = await _create_producto(client, auth_headers, "Pizza Delivery", "10000.00")

    body = {
        "tipo_entrega": "DELIVERY",
        "canal_origen": "WHATSAPP",
        "items": [
            {"producto_id": prod["id"], "cantidad": 1},
        ],
    }
    resp = await client.post("/api/v1/core/comandas", json=body, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["tipo_entrega"] == "DELIVERY"
    assert resp.json()["canal_origen"] == "WHATSAPP"
    assert resp.json()["numero_mesa"] is None


@pytest.mark.asyncio
async def test_create_comanda_invalid_tipo_entrega(client, auth_headers):
    """Invalid tipo_entrega should be rejected by Pydantic validator."""
    prod = await _create_producto(client, auth_headers, "Test Item", "1000.00")

    body = {
        "tipo_entrega": "INVALID_TYPE",
        "canal_origen": "WEB",
        "items": [
            {"producto_id": prod["id"], "cantidad": 1},
        ],
    }
    resp = await client.post("/api/v1/core/comandas", json=body, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_comanda_invalid_canal_origen(client, auth_headers):
    """Invalid canal_origen should be rejected by Pydantic validator."""
    prod = await _create_producto(client, auth_headers, "Test Item 2", "1000.00")

    body = {
        "tipo_entrega": "MESA",
        "canal_origen": "INVALID_CANAL",
        "numero_mesa": 1,
        "items": [
            {"producto_id": prod["id"], "cantidad": 1},
        ],
    }
    resp = await client.post("/api/v1/core/comandas", json=body, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_transition_with_invalid_estado_value(client, auth_headers):
    """PATCH with invalid estado string should return 422 (Pydantic validation)."""
    prod = await _create_producto(client, auth_headers, "Torta", "6000.00")
    create_resp = await _create_comanda(client, auth_headers, prod["id"])
    comanda_id = create_resp.json()["id"]

    resp = await _transition_estado(client, auth_headers, comanda_id, "INEXISTENT_ESTADO")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_comanda_with_item_notas(client, auth_headers):
    """Item-level notas should be stored."""
    prod = await _create_producto(client, auth_headers, "Pasta Custom", "8000.00")

    body = {
        "tipo_entrega": "MESA",
        "canal_origen": "PRESENCIAL",
        "numero_mesa": 3,
        "notas": "Mesa junto a la ventana",
        "items": [
            {
                "producto_id": prod["id"],
                "cantidad": 1,
                "notas": "Sin cebolla, extra ajo",
            },
        ],
    }
    resp = await client.post("/api/v1/core/comandas", json=body, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["notas"] == "Mesa junto a la ventana"
    assert data["items"][0]["notas"] == "Sin cebolla, extra ajo"


@pytest.mark.asyncio
async def test_create_comanda_with_prioridad(client, auth_headers):
    """Comanda with custom prioridad field."""
    prod = await _create_producto(client, auth_headers, "VIP Steak", "25000.00")

    resp = await _create_comanda(
        client, auth_headers, prod["id"], prioridad=5
    )
    assert resp.status_code == 201
    assert resp.json()["prioridad"] == 5
