"""Database engine, session factory, and RLS session context helpers."""

import inspect
import re
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str, **kwargs) -> AsyncEngine:
    echo = kwargs.pop("echo", False)
    extra: dict = {"echo": echo}
    connect_args = kwargs.pop("connect_args", {})

    # Cloud SQL Unix socket: asyncpg needs the socket path via connect_args,
    # not as a URL query parameter (SQLAlchemy doesn't pass it through).
    match = re.search(r"[?&]host=(/cloudsql/[^&]+)", database_url)
    if match:
        connect_args.setdefault("host", match.group(1))
        database_url = re.sub(r"[?&]host=/cloudsql/[^&]+", "", database_url)

    if "sqlite" not in database_url:
        extra["pool_size"] = kwargs.pop("pool_size", 5)
        extra["max_overflow"] = kwargs.pop("max_overflow", 10)
        extra["pool_pre_ping"] = kwargs.pop("pool_pre_ping", True)
        extra["pool_recycle"] = kwargs.pop("pool_recycle", 300)

    if connect_args:
        extra["connect_args"] = connect_args

    extra.update(kwargs)
    return create_async_engine(database_url, **extra)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def _uses_sqlite(session: AsyncSession) -> bool:
    bind = session.get_bind()
    if inspect.isawaitable(bind):
        bind.close()
        return False
    dialect = getattr(bind, "dialect", None)
    return getattr(dialect, "name", "") == "sqlite"


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """Set the RLS context for the current session."""
    safe_tid = str(UUID(str(tenant_id)))
    if _uses_sqlite(session):
        return

    # SET LOCAL does not support bind parameters in PostgreSQL.
    # Validate as UUID to prevent SQL injection, then use a literal.
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{safe_tid}'"))


async def set_qr_lookup_context(session: AsyncSession) -> None:
    """Allow the public QR flow to join against sucursales under RLS."""
    if _uses_sqlite(session):
        return
    await session.execute(text("SELECT set_config('app.allow_qr_lookup', 'true', true)"))


async def set_instance_lookup_context(session: AsyncSession, instance_name: str) -> None:
    """Allow a webhook transaction to resolve an Evolution instance by name under RLS."""
    if _uses_sqlite(session):
        return
    await session.execute(
        text("SELECT set_config('app.allow_instance_lookup', 'true', true)")
    )
    await session.execute(
        text("SELECT set_config('app.current_instance_name', :instance_name, true)"),
        {"instance_name": instance_name},
    )
