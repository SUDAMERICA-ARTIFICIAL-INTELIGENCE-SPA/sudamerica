"""Runtime schema guardrails for canales_service."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def ensure_canales_schema(engine: AsyncEngine) -> None:
    """Fail fast when the Alembic-managed canales tables are missing."""
    async with engine.begin() as connection:
        if connection.dialect.name == "sqlite":
            query = text(
                "SELECT 1 FROM sqlite_master "
                "WHERE type = 'table' AND name = :table_name"
            )
        else:
            query = text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = current_schema() AND table_name = :table_name"
            )

        result = await connection.execute(
            query,
            {"table_name": "evolution_instances"},
        )
        exists = result.scalar_one_or_none() == 1

    if not exists:
        raise RuntimeError(
            "Missing required table 'evolution_instances'. "
            "Run Alembic migrations before starting canales_service."
        )
