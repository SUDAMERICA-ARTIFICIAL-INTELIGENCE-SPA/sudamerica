"""Tests for the public mesa QR endpoint."""

from unittest.mock import ANY, AsyncMock, patch

import pytest

from app.routes import mesa_qr

from .conftest import TENANT_ID


@pytest.mark.asyncio
async def test_scan_mesa_qr_sets_lookup_contexts_and_redirects(client):
    mesa = {
        "id": "mesa-1",
        "numero": 12,
        "tenant_id": TENANT_ID,
        "sucursal_id": None,
        "activo": True,
        "sucursal_nombre": "Patio",
        "tenant_nombre": "Test Tenant",
    }

    with (
        patch("app.routes.mesa_qr.set_qr_lookup_context", new_callable=AsyncMock) as mock_qr_ctx,
        patch("app.routes.mesa_qr.set_instance_lookup_context", new_callable=AsyncMock) as mock_instance_ctx,
        patch("app.routes.mesa_qr.get_mesa_by_qr_token", new_callable=AsyncMock, return_value=mesa),
        patch("app.routes.mesa_qr._get_whatsapp_phone", new_callable=AsyncMock, return_value="+56912345678"),
    ):
        response = await client.get(
            "/api/v1/public/mesas/qr/qr-public-token",
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert response.headers["location"].startswith("https://wa.me/56912345678?text=")
    mock_qr_ctx.assert_awaited_once_with(ANY)
    mock_instance_ctx.assert_awaited_once_with(ANY, f"tenant-{TENANT_ID}")


class _FakeMappingsResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def first(self):
        return self._row


@pytest.mark.asyncio
async def test_get_whatsapp_phone_projects_only_needed_columns():
    db = AsyncMock()
    db.execute.return_value = _FakeMappingsResult(
        {
            "instance_name": "tenant-demo",
            "phone_number": "+56912345678",
            "status": "CONNECTED",
        }
    )

    phone = await mesa_qr._get_whatsapp_phone(db, "tenant-demo")

    query = str(db.execute.await_args.args[0])
    params = db.execute.await_args.args[1]

    assert phone == "+56912345678"
    assert "SELECT instance_name, phone_number, status" in query
    assert "SELECT *" not in query.upper()
    assert params == {"instance_name": "tenant-demo"}
