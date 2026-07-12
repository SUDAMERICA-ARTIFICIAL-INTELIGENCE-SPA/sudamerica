"""Alembic environment configuration — sync driver (psycopg2).

Uses importlib to load model files from each microservice without
conflicting on their shared ``app`` package name.
"""

import importlib.util
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# ---------------------------------------------------------------------------
# Ensure backend/ is in sys.path for shared package
# ---------------------------------------------------------------------------
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.base import Base  # noqa: E402

# ---------------------------------------------------------------------------
# Import ALL model classes so Base.metadata registers every table.
# We use importlib to avoid conflicts between microservices that all have
# an ``app`` package.
# ---------------------------------------------------------------------------
_MODEL_FILES = [
    # shared
    ("shared.tenant", "shared/models/tenant.py"),
    ("shared.sucursal", "shared/models/sucursal.py"),
    ("shared.mesa", "shared/models/mesa.py"),
    # api_execute
    ("api_execute.usuario", "api_execute/app/models/usuario.py"),
    ("api_execute.categoria", "api_execute/app/models/categoria.py"),
    ("api_execute.producto", "api_execute/app/models/producto.py"),
    ("api_execute.lead", "api_execute/app/models/lead.py"),
    ("api_execute.venta", "api_execute/app/models/venta.py"),
    ("api_execute.stripe_event", "api_execute/app/models/stripe_event.py"),
    ("api_execute.smart_alert", "api_execute/app/models/smart_alert.py"),
    ("api_execute.sales_target", "api_execute/app/models/sales_target.py"),
    ("api_execute.comanda", "api_execute/app/models/comanda.py"),
    ("api_execute.delivery", "api_execute/app/models/delivery.py"),
    ("api_execute.modifier", "api_execute/app/models/modifier.py"),
    ("api_execute.menu_import", "api_execute/app/models/menu_import.py"),
    ("api_execute.password_reset_token", "api_execute/app/models/password_reset_token.py"),
    ("api_execute.suministro", "api_execute/app/models/suministro.py"),
    ("api_execute.api_key_audit", "api_execute/app/models/api_key_audit.py"),
    ("api_execute.platform_config", "api_execute/app/models/platform_config.py"),
    ("api_execute.reservacion", "api_execute/app/models/reservacion.py"),
    ("api_execute.subentidad", "api_execute/app/models/subentidad.py"),
    # callback_manual
    ("callback_manual.revision_humana", "callback_manual/app/models/revision_humana.py"),
    # tasks
    ("tasks.task_log", "tasks/app/models/task_log.py"),
    # canales_service
    ("canales_service.evolution_instance", "canales_service/app/models/evolution_instance.py"),
]

for _mod_name, _rel_path in _MODEL_FILES:
    _file_path = str(backend_dir / _rel_path)
    _spec = importlib.util.spec_from_file_location(_mod_name, _file_path)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)

# ---------------------------------------------------------------------------
# Alembic config
# ---------------------------------------------------------------------------
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DATABASE_URL env var overrides alembic.ini (used in deploy / Cloud Build).
# Automatically convert asyncpg URLs to psycopg2 for Alembic compatibility.
database_url = os.getenv("DATABASE_URL")
if database_url:
    database_url = database_url.replace(
        "postgresql+asyncpg://", "postgresql://"
    )
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata

# Tables that exist in the DB but have no SQLAlchemy model — Alembic should
# ignore them (never DROP or ALTER).
_UNMANAGED_TABLES = frozenset({
    "sucursal_producto_precios",  # raw SQL only, no ORM model
    # AI chat / knowledge tables — defined in infra/001_schema.sql and accessed
    # via raw SQL from api_execute (no ORM models). Alembic must never DROP or
    # ALTER them on autogenerate.
    "agente_config",
    "ai_conversations",
    "ai_embeddings",
    "contacts",
    "llm_provider_keys",
    "sessions",
    "tenant_knowledge",
})


def include_object(obj, name, type_, reflected, compare_to):
    """Skip tables that exist in the DB but are not managed by models."""
    if type_ == "table" and name in _UNMANAGED_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    """Generate SQL script without connecting to the database."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
