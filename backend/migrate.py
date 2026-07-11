#!/usr/bin/env python3
"""Run Alembic migrations programmatically for deploy pipelines.

Usage:
    DATABASE_URL=postgresql://user:pass@host:5432/sudamerica python migrate.py

Exit codes:
    0 — migrations applied (or already at head)
    1 — error
"""

import logging
import os
import sys
from contextlib import contextmanager
from urllib.parse import parse_qs, urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("migrate")


def _sync_url(url: str) -> str:
    """Convert async driver URLs to sync psycopg2 for Alembic."""
    return url.replace("postgresql+asyncpg://", "postgresql://")


def _psycopg2_connect_kwargs(url: str) -> dict:
    """Parse a postgres URL into psycopg2 connect kwargs.

    Supports Cloud SQL Unix socket via ``?host=/cloudsql/...`` query param.
    """
    parsed = urlparse(url)
    kwargs = {
        "user": parsed.username,
        "password": parsed.password,
        "dbname": parsed.path.lstrip("/"),
    }
    query = parse_qs(parsed.query)
    if "host" in query:
        kwargs["host"] = query["host"][0]
    else:
        kwargs["host"] = parsed.hostname
        if parsed.port:
            kwargs["port"] = parsed.port
    return kwargs


def _set_role_rls(url: str, *, bypass: bool) -> None:
    """Grant or revoke BYPASSRLS on the postgres role.

    Alembic introspection under FORCE RLS fails silently because the role
    cannot read catalog rows filtered by tenant_isolation policies. Granting
    BYPASSRLS for the migration window lets DDL run; we revoke immediately
    after so production security posture is restored.
    """
    import psycopg2

    clause = "BYPASSRLS" if bypass else "NOBYPASSRLS"
    kwargs = _psycopg2_connect_kwargs(url)
    conn = psycopg2.connect(**kwargs)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f"ALTER ROLE postgres {clause};")
        logger.info("Applied ALTER ROLE postgres %s", clause)
    finally:
        conn.close()


@contextmanager
def _bypass_rls(url: str):
    _set_role_rls(url, bypass=True)
    try:
        yield
    finally:
        try:
            _set_role_rls(url, bypass=False)
        except Exception:
            logger.exception(
                "CRITICAL: failed to revoke BYPASSRLS on postgres role. "
                "Run manually: ALTER ROLE postgres NOBYPASSRLS;"
            )
            raise


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable is required")
        return 1

    database_url = _sync_url(database_url)
    os.environ["DATABASE_URL"] = database_url

    # Remove backend/ from sys.path to avoid local ``alembic/`` dir
    # shadowing the ``alembic`` package (same trick as run_alembic.py).
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path = [p for p in sys.path if os.path.abspath(p) != backend_dir]

    from alembic import command
    from alembic.config import Config

    # Re-add backend dir so env.py can import shared/models.
    sys.path.insert(0, backend_dir)

    try:
        alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)

        with _bypass_rls(database_url):
            logger.info("Running alembic upgrade head …")
            command.upgrade(alembic_cfg, "head")
        logger.info("Migrations applied successfully.")
        return 0

    except Exception:
        logger.exception("Migration failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
