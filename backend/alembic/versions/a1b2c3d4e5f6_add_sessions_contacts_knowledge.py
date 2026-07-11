"""Add sessions, contacts, and tenant_knowledge tables.

Revision ID: a1b2c3d4e5f6
Revises: 4b9b2f6f2d6d
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "a1b2c3d4e5f6"
down_revision = "4b9b2f6f2d6d"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return set(inspector.get_table_names(schema="public"))


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name, schema="public")}


_ALLOWED_TABLES = {"contacts", "sessions", "tenant_knowledge"}


def _ensure_tenant_policy(table_name: str) -> None:
    if table_name not in _ALLOWED_TABLES:
        raise ValueError(f"Unknown table: {table_name}")
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")  # noqa: S608
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")  # noqa: S608
    op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name}")  # noqa: S608
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table_name}
            FOR ALL
            USING (tenant_id::text = current_setting('app.current_tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true))
        """  # noqa: S608
    )


def _create_contacts() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "phone", name="uq_contacts_tenant_phone"),
    )


def _create_sessions() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", UUID(as_uuid=True), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("lead_id", UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(50), nullable=False, server_default=sa.text("'WEB'")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("status IN ('ACTIVE', 'CLOSED', 'HUMAN_HANDOFF')", name="ck_sessions_status"),
    )


def _create_tenant_knowledge() -> None:
    op.create_table(
        "tenant_knowledge",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )


def _add_ai_conversation_columns() -> None:
    ai_conversation_columns = _column_names("ai_conversations")
    if "session_id" not in ai_conversation_columns:
        op.add_column("ai_conversations", sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=True))
    if "external_wa_id" not in ai_conversation_columns:
        op.add_column("ai_conversations", sa.Column("external_wa_id", sa.String(255), nullable=True))
    if "status" not in ai_conversation_columns:
        op.add_column("ai_conversations", sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'SENT'")))


def _add_agente_config_columns() -> None:
    agente_config_columns = _column_names("agente_config")
    if "session_timeout_minutes" not in agente_config_columns:
        op.add_column(
            "agente_config",
            sa.Column("session_timeout_minutes", sa.Integer(), nullable=False, server_default=sa.text("30")),
        )


def _create_indexes() -> None:
    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_contacts_tenant_phone ON contacts (tenant_id, phone)",
        "CREATE INDEX IF NOT EXISTS idx_contacts_tenant_activo ON contacts (tenant_id, activo)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_tenant_contact_status ON sessions (tenant_id, contact_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_tenant_status ON sessions (tenant_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_tenant_created ON sessions (tenant_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_ai_conv_session ON ai_conversations (session_id)",
        "CREATE INDEX IF NOT EXISTS idx_tenant_knowledge_tenant_type ON tenant_knowledge (tenant_id, type)",
        "CREATE INDEX IF NOT EXISTS idx_tenant_knowledge_tenant_priority ON tenant_knowledge (tenant_id, priority DESC)",
    ):
        op.execute(statement)


def upgrade() -> None:
    existing_tables = _table_names()

    if "contacts" not in existing_tables:
        _create_contacts()
    if "sessions" not in existing_tables:
        _create_sessions()
    if "tenant_knowledge" not in existing_tables:
        _create_tenant_knowledge()

    _add_ai_conversation_columns()
    _add_agente_config_columns()
    _create_indexes()

    for table_name in ("contacts", "sessions", "tenant_knowledge"):
        _ensure_tenant_policy(table_name)


def downgrade() -> None:
    raise NotImplementedError("Forward-only migration")
