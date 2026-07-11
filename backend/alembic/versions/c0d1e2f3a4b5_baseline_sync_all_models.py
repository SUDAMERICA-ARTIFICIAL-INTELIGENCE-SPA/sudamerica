"""Baseline sync — register all ORM-managed tables with Alembic.

Revision ID: c0d1e2f3a4b5
Revises: b7c8d9e0f1a2
Create Date: 2026-03-31 12:00:00.000000

This is a no-op migration.  The tables listed below were created via
the SQL scripts in ``backend/infra/`` (008–015) and already exist in
production.  From this point on, every schema change MUST go through
Alembic (``alembic revision --autogenerate -m "description"``).

Tables now tracked by Alembic via ORM models:
  - sucursales            (shared/models/sucursal.py)
  - mesas                 (api_execute/app/models/mesa.py)
  - comandas              (api_execute/app/models/comanda.py)
  - comanda_items         (api_execute/app/models/comanda.py)
  - modifier_groups       (api_execute/app/models/modifier.py)
  - modifiers             (api_execute/app/models/modifier.py)
  - producto_modifier_groups (api_execute/app/models/modifier.py)
  - password_reset_tokens (api_execute/app/models/password_reset_token.py)
  - suministros           (api_execute/app/models/suministro.py)
  - recetas               (api_execute/app/models/suministro.py)
  - api_key_audit         (api_execute/app/models/api_key_audit.py)
  - platform_config       (api_execute/app/models/platform_config.py)
  - reservaciones         (api_execute/app/models/reservacion.py)

After deploying this revision, run on production:
    DATABASE_URL=postgresql://... alembic stamp head
"""

from typing import Sequence, Union


revision: str = "c0d1e2f3a4b5"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All tables already exist in production (created via infra/*.sql).
    # This migration only serves to register them in Alembic's history.
    pass


def downgrade() -> None:
    # Not reversible — these tables predate Alembic management.
    pass
