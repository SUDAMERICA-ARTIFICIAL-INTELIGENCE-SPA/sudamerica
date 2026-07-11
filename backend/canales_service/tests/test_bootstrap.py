"""Tests for canales_service schema guards."""

from pathlib import Path

import pytest
from app.bootstrap import ensure_canales_schema
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.asyncio
async def test_ensure_canales_schema_accepts_existing_table(tmp_path: Path):
    db_path = tmp_path / "canales_schema.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async with engine.begin() as connection:
        await connection.execute(text("CREATE TABLE tenants (id TEXT PRIMARY KEY)"))
        await connection.execute(
            text("CREATE TABLE evolution_instances (id TEXT PRIMARY KEY)")
        )

    await ensure_canales_schema(engine)
    await engine.dispose()


@pytest.mark.asyncio
async def test_ensure_canales_schema_fails_when_table_is_missing(tmp_path: Path):
    db_path = tmp_path / "canales_schema_missing.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async with engine.begin() as connection:
        await connection.execute(text("CREATE TABLE tenants (id TEXT PRIMARY KEY)"))

    with pytest.raises(RuntimeError, match="evolution_instances"):
        await ensure_canales_schema(engine)

    await engine.dispose()
