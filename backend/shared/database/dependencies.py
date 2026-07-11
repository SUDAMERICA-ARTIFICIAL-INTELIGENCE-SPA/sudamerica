"""FastAPI dependency for database sessions with RLS."""

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.database.session import set_tenant_context


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield a DB session with tenant context set via RLS."""
    session_factory: async_sessionmaker = request.app.state.session_factory
    async with session_factory() as session:
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            await set_tenant_context(session, str(tenant_id))
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


async def get_db_superadmin_bypass(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield a DB session that bypasses tenant RLS.

    **WARNING**: Only use in SUPERADMIN-protected routes (sudamerica-admin panel).
    Sets ``app.is_superadmin = 'true'`` so that the ``superadmin_bypass``
    RLS policies on each table allow cross-tenant reads and writes.
    """
    session_factory: async_sessionmaker = request.app.state.session_factory
    async with session_factory() as session:
        await session.execute(text("SET LOCAL app.is_superadmin = 'true'"))
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


# Backward compat alias — prefer get_db_superadmin_bypass in new code
get_db_admin = get_db_superadmin_bypass
