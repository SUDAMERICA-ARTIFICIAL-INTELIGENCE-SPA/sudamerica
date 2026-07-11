"""Tests for AI conversation summary and weekly-activity endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text

from .conftest import TENANT_ID, TestSessionFactory


_CREATE_AI_CONV_SQL = """
CREATE TABLE IF NOT EXISTS ai_conversations (
    id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, usuario_id TEXT,
    lead_id TEXT, session_id TEXT, role TEXT NOT NULL DEFAULT 'assistant',
    content TEXT NOT NULL, tokens_used INTEGER, modelo TEXT, canal TEXT,
    external_wa_id TEXT, media_url TEXT, media_type TEXT,
    status TEXT NOT NULL DEFAULT 'SENT',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""

_CREATE_REVISION_SQL = """
CREATE TABLE IF NOT EXISTS revision_humana (
    id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, lead_id TEXT,
    mensaje_original TEXT, respuesta_ia TEXT, confianza REAL,
    accion TEXT, procesado INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP
)"""

_INSERT_MSG_SQL = """
INSERT INTO ai_conversations (id, tenant_id, lead_id, role, content, tokens_used, canal, status, created_at)
VALUES (:id, :tid, :lid, :role, :content, :tokens, :canal, 'SENT', :created_at)"""


async def _seed_lead_messages(session, tenant_id, lead_id, count, canal, base_tokens, now, hour_offset):
    """Insert N test messages for a lead."""
    for i in range(count):
        await session.execute(text(_INSERT_MSG_SQL), {
            "id": str(uuid.uuid4()), "tid": tenant_id, "lid": lead_id,
            "role": "assistant" if i % 2 else "user",
            "content": f"Test message {lead_id[:8]} {i}",
            "tokens": base_tokens + i * 50, "canal": canal,
            "created_at": (now - timedelta(hours=hour_offset - i)).isoformat(),
        })


@pytest_asyncio.fixture(autouse=True)
async def _seed_ai_conversations():
    """Seed ai_conversations table with test data."""
    now = datetime.now(timezone.utc)
    lead1, lead2 = str(uuid.uuid4()), str(uuid.uuid4())

    async with TestSessionFactory() as session:
        await session.execute(text(_CREATE_AI_CONV_SQL))
        await session.execute(text(_CREATE_REVISION_SQL))
        await session.execute(text("DELETE FROM ai_conversations WHERE tenant_id = :tid"), {"tid": TENANT_ID})
        await _seed_lead_messages(session, TENANT_ID, lead1, 3, "WHATSAPP", 100, now, 3)
        await _seed_lead_messages(session, TENANT_ID, lead2, 2, "WEB", 200, now, 1)
        await session.commit()
    yield


@pytest.mark.asyncio
async def test_list_ai_conversations(client, auth_headers):
    """GET /ai-conversations returns paginated conversation summaries."""
    r = await client.get("/api/v1/core/ai-conversations", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "meta" in data
    assert "total" in data["meta"]
    assert "page" in data["meta"]
    assert "page_size" in data["meta"]
    assert "total_pages" in data["meta"]
    assert data["meta"]["total"] >= 2  # at least 2 lead conversations


@pytest.mark.asyncio
async def test_list_ai_conversations_pagination(client, auth_headers):
    """GET /ai-conversations respects page_size."""
    r = await client.get(
        "/api/v1/core/ai-conversations?page_size=1&page=1",
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["data"]) <= 1


@pytest.mark.asyncio
async def test_list_ai_conversations_requires_auth(client):
    """GET /ai-conversations returns 401 without auth."""
    r = await client.get("/api/v1/core/ai-conversations")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_weekly_activity(client, auth_headers):
    """GET /metricas/weekly-activity returns 7 day-of-week entries."""
    r = await client.get(
        "/api/v1/core/metricas/weekly-activity",
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 7
    for point in data:
        assert "day" in point
        assert "ia" in point
        assert "humano" in point


@pytest.mark.asyncio
async def test_weekly_activity_day_labels(client, auth_headers):
    """Weekly activity uses Spanish day labels."""
    r = await client.get(
        "/api/v1/core/metricas/weekly-activity",
        headers=auth_headers,
    )
    data = r.json()
    labels = [p["day"] for p in data]
    assert labels == ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


@pytest.mark.asyncio
async def test_menu_engineering(client, auth_headers):
    """GET /metricas/menu-engineering returns list (empty if no ventas)."""
    r = await client.get(
        "/api/v1/core/metricas/menu-engineering",
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_menu_engineering_requires_auth(client):
    """GET /metricas/menu-engineering returns 401 without auth."""
    r = await client.get("/api/v1/core/metricas/menu-engineering")
    assert r.status_code in (401, 403)
