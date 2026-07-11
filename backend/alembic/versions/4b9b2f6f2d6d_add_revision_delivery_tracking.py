"""Add delivery tracking fields to revision_humana.

Revision ID: 4b9b2f6f2d6d
Revises: a4ca16a0a022
Create Date: 2026-03-12 10:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4b9b2f6f2d6d"
down_revision: Union[str, None] = "a4ca16a0a022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name, schema="public")}


def upgrade() -> None:
    revision_columns = _column_names("revision_humana")

    if "delivery_status" not in revision_columns:
        op.add_column(
            "revision_humana",
            sa.Column(
                "delivery_status",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'PENDING'"),
            ),
        )
    if "delivery_timestamp" not in revision_columns:
        op.add_column(
            "revision_humana",
            sa.Column("delivery_timestamp", sa.DateTime(timezone=True), nullable=True),
        )
    if "delivery_error" not in revision_columns:
        op.add_column(
            "revision_humana",
            sa.Column("delivery_error", sa.Text(), nullable=True),
        )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_revision_tenant_delivery_status "
        "ON revision_humana (tenant_id, delivery_status);"
    )


def downgrade() -> None:
    raise NotImplementedError("Forward-only migration")
