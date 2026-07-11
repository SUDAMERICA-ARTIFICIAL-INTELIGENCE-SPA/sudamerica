"""Initial schema — 11 tables

Revision ID: cfc9ea1a4fc2
Revises:
Create Date: 2026-02-26 12:16:42.556825

Baseline migration: schema was created via infra/001_schema.sql,
002_rls_policies.sql, and 003_indexes.sql.
This is an empty migration to mark the starting point for alembic.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cfc9ea1a4fc2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema already applied via SQL init scripts (infra/)
    pass


def downgrade() -> None:
    # Not reversible — would need to drop all tables
    pass
