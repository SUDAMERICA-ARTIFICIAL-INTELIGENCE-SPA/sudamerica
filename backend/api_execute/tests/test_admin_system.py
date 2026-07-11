"""Tests for admin system endpoints."""

import pytest

from .conftest import TENANT_ID, make_token


def _superadmin_headers() -> dict[str, str]:
    token = make_token(role="SUPERADMIN", email="admin@sudamerica.ai")
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
    }


@pytest.mark.asyncio
async def test_data_model_requires_superadmin(client, auth_headers):
    resp = await client.get("/api/v1/admin/system/data-model", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_data_model_snapshot_returns_tables_and_enums(client):
    resp = await client.get("/api/v1/admin/system/data-model", headers=_superadmin_headers())
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["summary"]["total_tables"] >= 2
    assert payload["summary"]["total_columns"] >= 1
    assert any(enum_item["name"] == "UserRole" for enum_item in payload["enums"])

    tables = {table["name"]: table for table in payload["tables"]}
    assert "tenants" in tables
    assert "usuarios" in tables
    assert tables["usuarios"]["tenant_scoped"] is True
    assert any(column["name"] == "email" for column in tables["usuarios"]["columns"])
