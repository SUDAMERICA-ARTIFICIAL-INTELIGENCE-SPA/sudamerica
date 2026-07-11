"""Tests for tenant settings and onboarding config persistence."""

import pytest


@pytest.mark.asyncio
async def test_tenant_config_patch_merges_nested_onboarding(client, auth_headers):
    first = await client.patch(
        "/api/v1/core/tenants/me",
        headers=auth_headers,
        json={
            "config": {
                "tipo_comida": "pizzas",
                "onboarding": {
                    "required": True,
                    "started_at": "2026-03-15T00:00:00+00:00",
                },
            }
        },
    )
    assert first.status_code == 200

    second = await client.patch(
        "/api/v1/core/tenants/me",
        headers=auth_headers,
        json={
            "config": {
                "onboarding": {
                    "business_completed_at": "2026-03-15T01:00:00+00:00",
                },
            }
        },
    )
    assert second.status_code == 200

    current = await client.get("/api/v1/core/tenants/me", headers=auth_headers)
    assert current.status_code == 200
    config = current.json()["config"]
    assert config["tipo_comida"] == "pizzas"
    assert config["onboarding"]["required"] is True
    assert config["onboarding"]["started_at"] == "2026-03-15T00:00:00+00:00"
    assert config["onboarding"]["business_completed_at"] == "2026-03-15T01:00:00+00:00"
