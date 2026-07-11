"""Align existing tenant tables with runtime expectations.

Revision ID: a4ca16a0a022
Revises: 6f6d4f7bf859
Create Date: 2026-03-11 18:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4ca16a0a022"
down_revision: Union[str, None] = "6f6d4f7bf859"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_TABLES = (
    "usuarios",
    "categorias",
    "productos",
    "leads",
    "ventas",
    "agente_config",
    "revision_humana",
    "ai_conversations",
    "ai_embeddings",
    "smart_alerts",
    "sales_targets",
    "evolution_instances",
    "llm_provider_keys",
    "task_logs",
)


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name, schema="public")}


_ALLOWED_TABLES = set(TENANT_TABLES)


def _apply_tenant_rls(table_name: str) -> None:
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


def _add_agente_config_columns() -> None:
    existing = _column_names("agente_config")
    new_cols = [
        ("auto_respuesta_whatsapp", sa.Boolean(), False, sa.text("true")),
        ("outbound_proactivo", sa.Boolean(), False, sa.text("false")),
        ("outbound_horario_inicio", sa.String(length=5), True, None),
        ("outbound_horario_fin", sa.String(length=5), True, None),
        ("outbound_mensaje_template", sa.Text(), True, None),
    ]
    for name, col_type, nullable, default in new_cols:
        if name not in existing:
            kwargs = {"nullable": nullable}
            if default is not None:
                kwargs["server_default"] = default
            op.add_column("agente_config", sa.Column(name, col_type, **kwargs))


def _add_revision_humana_activo() -> None:
    revision_columns = _column_names("revision_humana")
    if "activo" not in revision_columns:
        op.add_column(
            "revision_humana",
            sa.Column(
                "activo",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )


def _create_revision_index() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_revision_tenant_activo_procesado "
        "ON revision_humana (tenant_id, activo, procesado);"
    )


def upgrade() -> None:
    _add_agente_config_columns()
    _add_revision_humana_activo()
    _create_revision_index()

    for table_name in TENANT_TABLES:
        _apply_tenant_rls(table_name)


def downgrade() -> None:
    raise NotImplementedError("Forward-only migration")
