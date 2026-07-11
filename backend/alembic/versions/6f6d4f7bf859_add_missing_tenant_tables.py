"""Add missing tenant-scoped tables used by active services.

Revision ID: 6f6d4f7bf859
Revises: cfc9ea1a4fc2
Create Date: 2026-03-11 18:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "6f6d4f7bf859"
down_revision: Union[str, None] = "cfc9ea1a4fc2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return set(inspector.get_table_names(schema="public"))


_ALLOWED_TABLES = {
    "smart_alerts",
    "sales_targets",
    "evolution_instances",
    "llm_provider_keys",
    "task_logs",
}


def _enable_tenant_rls(table_name: str) -> None:
    if table_name not in _ALLOWED_TABLES:
        raise ValueError(f"Unknown table: {table_name}")
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))  # noqa: S608
    op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))  # noqa: S608
    op.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name}"))  # noqa: S608
    op.execute(
        sa.text(
            f"""
            CREATE POLICY tenant_isolation ON {table_name}
                FOR ALL
                USING (tenant_id::text = current_setting('app.current_tenant_id', true))
                WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true))
            """  # noqa: S608
        )
    )


def _create_smart_alerts() -> None:
    op.create_table(
        "smart_alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tipo",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "lead_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column(
            "leido",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "activo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def _create_sales_targets() -> None:
    op.create_table(
        "sales_targets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asesor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("periodo", sa.String(length=7), nullable=False),
        sa.Column(
            "meta_ventas",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "meta_leads",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "meta_conversion",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "activo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def _create_evolution_instances() -> None:
    op.create_table(
        "evolution_instances",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "activo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("instance_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'DISCONNECTED'"),
        ),
        sa.Column("phone_number", sa.String(length=50), nullable=True),
        sa.Column("evo_token", sa.String(length=255), nullable=True),
    )


def _create_llm_provider_keys() -> None:
    op.create_table(
        "llm_provider_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("default_model", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
    )


def _create_task_logs() -> None:
    op.create_table(
        "task_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("destinatario", sa.String(length=255), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column(
            "estado",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'PENDIENTE'"),
        ),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def _create_unique_indexes() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_targets_team_period
        ON sales_targets (tenant_id, periodo)
        WHERE asesor_id IS NULL;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_targets_advisor_period
        ON sales_targets (tenant_id, asesor_id, periodo)
        WHERE asesor_id IS NOT NULL;
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_evolution_instances_instance_name "
        "ON evolution_instances (instance_name);"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_llm_key_tenant_provider "
        "ON llm_provider_keys (tenant_id, provider);"
    )


def _create_lookup_indexes() -> None:
    for statement in (
        "CREATE INDEX IF NOT EXISTS ix_smart_alerts_tenant_id ON smart_alerts (tenant_id);",
        "CREATE INDEX IF NOT EXISTS idx_smart_alerts_tenant_leido_created ON smart_alerts (tenant_id, leido, created_at DESC);",
        "CREATE INDEX IF NOT EXISTS ix_sales_targets_tenant_id ON sales_targets (tenant_id);",
        "CREATE INDEX IF NOT EXISTS idx_sales_targets_tenant_periodo ON sales_targets (tenant_id, periodo);",
        "CREATE INDEX IF NOT EXISTS ix_evolution_instances_tenant_id ON evolution_instances (tenant_id);",
        "CREATE INDEX IF NOT EXISTS idx_evolution_instances_tenant_activo ON evolution_instances (tenant_id, activo);",
        "CREATE INDEX IF NOT EXISTS ix_llm_provider_keys_tenant_id ON llm_provider_keys (tenant_id);",
        "CREATE INDEX IF NOT EXISTS ix_task_logs_tenant_id ON task_logs (tenant_id);",
        "CREATE INDEX IF NOT EXISTS idx_task_logs_tenant_estado ON task_logs (tenant_id, estado);",
        "CREATE INDEX IF NOT EXISTS idx_task_logs_tenant_created ON task_logs (tenant_id, created_at DESC);",
    ):
        op.execute(statement)


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    existing_tables = _table_names()

    if "smart_alerts" not in existing_tables:
        _create_smart_alerts()
    if "sales_targets" not in existing_tables:
        _create_sales_targets()
    if "evolution_instances" not in existing_tables:
        _create_evolution_instances()
    if "llm_provider_keys" not in existing_tables:
        _create_llm_provider_keys()
    if "task_logs" not in existing_tables:
        _create_task_logs()

    _create_unique_indexes()
    _create_lookup_indexes()

    for table_name in _ALLOWED_TABLES:
        _enable_tenant_rls(table_name)


def downgrade() -> None:
    raise NotImplementedError("Forward-only migration")
