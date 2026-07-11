"""Harden tenant integrity, webhook lookup RLS, and LLM key encryption.

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-03-12 14:00:00.000000
"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa

from shared.utils import encrypt_secret


revision = "b7c8d9e0f1a2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def _constraint_exists(name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_constraint
            WHERE conname = :name
            """
        ),
        {"name": name},
    )
    return result.scalar_one_or_none() is not None


def _ensure_unique_pair(table_name: str, constraint_name: str) -> None:
    if _constraint_exists(constraint_name):
        return
    op.execute(
        sa.text(
            f"ALTER TABLE {table_name} "
            f"ADD CONSTRAINT {constraint_name} UNIQUE (tenant_id, id)"
        )
    )


def _ensure_composite_fk(
    constraint_name: str,
    source_table: str,
    referent_table: str,
    local_columns: list[str],
    remote_columns: list[str],
    *,
    ondelete: str,
) -> None:
    if _constraint_exists(constraint_name):
        return
    op.create_foreign_key(
        constraint_name,
        source_table,
        referent_table,
        local_columns,
        remote_columns,
        ondelete=ondelete,
    )


def _encrypt_legacy_llm_keys() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, api_key
            FROM llm_provider_keys
            WHERE api_key IS NOT NULL
              AND api_key NOT LIKE 'enc:v1:%'
            """
        )
    ).mappings().all()
    if not rows:
        return

    master_key = os.getenv("LLM_PROVIDER_KEY_MASTER_KEY", "").strip()
    if not master_key:
        raise RuntimeError(
            "LLM_PROVIDER_KEY_MASTER_KEY is required to migrate legacy llm_provider_keys"
        )

    for row in rows:
        bind.execute(
            sa.text(
                """
                UPDATE llm_provider_keys
                SET api_key = :api_key
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "api_key": encrypt_secret(row["api_key"], master_key),
            },
        )


def _drop_ventas_usuario_not_null() -> None:
    op.execute("ALTER TABLE ventas ALTER COLUMN usuario_id DROP NOT NULL")


def _add_unique_pair_constraints() -> None:
    for table_name, constraint_name in (
        ("categorias", "uq_categorias_tenant_id_id"),
        ("usuarios", "uq_usuarios_tenant_id_id"),
        ("leads", "uq_leads_tenant_id_id"),
        ("productos", "uq_productos_tenant_id_id"),
        ("contacts", "uq_contacts_tenant_id_id"),
        ("sessions", "uq_sessions_tenant_id_id"),
    ):
        _ensure_unique_pair(table_name, constraint_name)


def _clean_orphaned_productos_categoria() -> None:
    op.execute(
        """
        UPDATE productos p
        SET categoria_id = NULL
        WHERE categoria_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM categorias c
              WHERE c.id = p.categoria_id
                AND c.tenant_id = p.tenant_id
          )
        """
    )


def _clean_orphaned_leads_asignado() -> None:
    op.execute(
        """
        UPDATE leads l
        SET asignado_a = NULL
        WHERE asignado_a IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM usuarios u
              WHERE u.id = l.asignado_a
                AND u.tenant_id = l.tenant_id
          )
        """
    )


def _clean_orphaned_ventas() -> None:
    op.execute(
        """
        UPDATE ventas v
        SET lead_id = NULL
        WHERE lead_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM leads l
              WHERE l.id = v.lead_id
                AND l.tenant_id = v.tenant_id
          )
        """
    )
    op.execute(
        """
        UPDATE ventas v
        SET producto_id = NULL
        WHERE producto_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM productos p
              WHERE p.id = v.producto_id
                AND p.tenant_id = v.tenant_id
          )
        """
    )
    op.execute(
        """
        UPDATE ventas v
        SET usuario_id = NULL
        WHERE usuario_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM usuarios u
              WHERE u.id = v.usuario_id
                AND u.tenant_id = v.tenant_id
          )
        """
    )


def _clean_orphaned_revision_humana() -> None:
    op.execute(
        """
        UPDATE revision_humana r
        SET lead_id = NULL
        WHERE lead_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM leads l
              WHERE l.id = r.lead_id
                AND l.tenant_id = r.tenant_id
          )
        """
    )
    op.execute(
        """
        UPDATE revision_humana r
        SET operador_id = NULL
        WHERE operador_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM usuarios u
              WHERE u.id = r.operador_id
                AND u.tenant_id = r.tenant_id
          )
        """
    )


def _clean_orphaned_ai_conversations() -> None:
    op.execute(
        """
        UPDATE ai_conversations c
        SET usuario_id = NULL
        WHERE usuario_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM usuarios u
              WHERE u.id = c.usuario_id
                AND u.tenant_id = c.tenant_id
          )
        """
    )
    op.execute(
        """
        UPDATE ai_conversations c
        SET lead_id = NULL
        WHERE lead_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM leads l
              WHERE l.id = c.lead_id
                AND l.tenant_id = c.tenant_id
          )
        """
    )
    op.execute(
        """
        UPDATE ai_conversations c
        SET session_id = NULL
        WHERE session_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM sessions s
              WHERE s.id = c.session_id
                AND s.tenant_id = c.tenant_id
          )
        """
    )


def _clean_orphaned_sessions() -> None:
    op.execute(
        """
        UPDATE sessions s
        SET lead_id = NULL
        WHERE lead_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM leads l
              WHERE l.id = s.lead_id
                AND l.tenant_id = s.tenant_id
          )
        """
    )
    op.execute(
        """
        DELETE FROM sessions s
        WHERE NOT EXISTS (
            SELECT 1
            FROM contacts c
            WHERE c.id = s.contact_id
              AND c.tenant_id = s.tenant_id
        )
        """
    )


def _clean_orphaned_sales_targets() -> None:
    op.execute(
        """
        UPDATE sales_targets t
        SET asesor_id = NULL
        WHERE asesor_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM usuarios u
              WHERE u.id = t.asesor_id
                AND u.tenant_id = t.tenant_id
          )
        """
    )


def _clean_orphaned_smart_alerts() -> None:
    op.execute(
        """
        UPDATE smart_alerts a
        SET lead_id = NULL
        WHERE lead_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM leads l
              WHERE l.id = a.lead_id
                AND l.tenant_id = a.tenant_id
          )
        """
    )


_COMPOSITE_FK_SPECS = [
    ("fk_productos_categoria_tenant", "productos", "categorias", "categoria_id", "SET NULL"),
    ("fk_leads_asignado_a_tenant", "leads", "usuarios", "asignado_a", "SET NULL"),
    ("fk_ventas_lead_tenant", "ventas", "leads", "lead_id", "SET NULL"),
    ("fk_ventas_producto_tenant", "ventas", "productos", "producto_id", "SET NULL"),
    ("fk_ventas_usuario_tenant", "ventas", "usuarios", "usuario_id", "SET NULL"),
    ("fk_revision_humana_lead_tenant", "revision_humana", "leads", "lead_id", "SET NULL"),
    ("fk_revision_humana_operador_tenant", "revision_humana", "usuarios", "operador_id", "SET NULL"),
    ("fk_sessions_contact_tenant", "sessions", "contacts", "contact_id", "RESTRICT"),
    ("fk_sessions_lead_tenant", "sessions", "leads", "lead_id", "SET NULL"),
    ("fk_ai_conversations_usuario_tenant", "ai_conversations", "usuarios", "usuario_id", "SET NULL"),
    ("fk_ai_conversations_lead_tenant", "ai_conversations", "leads", "lead_id", "SET NULL"),
    ("fk_ai_conversations_session_tenant", "ai_conversations", "sessions", "session_id", "SET NULL"),
    ("fk_sales_targets_asesor_tenant", "sales_targets", "usuarios", "asesor_id", "SET NULL"),
    ("fk_smart_alerts_lead_tenant", "smart_alerts", "leads", "lead_id", "SET NULL"),
]


def _add_composite_foreign_keys() -> None:
    for name, src, ref, col, on_del in _COMPOSITE_FK_SPECS:
        _ensure_composite_fk(name, src, ref, ["tenant_id", col], ["tenant_id", "id"], ondelete=on_del)


def _update_evolution_instances_rls() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON evolution_instances")
    op.execute("DROP POLICY IF EXISTS evolution_instances_read ON evolution_instances")
    op.execute("DROP POLICY IF EXISTS evolution_instances_write ON evolution_instances")
    op.execute(
        """
        CREATE POLICY evolution_instances_read ON evolution_instances
            FOR SELECT
            USING (
                tenant_id::text = current_setting('app.current_tenant_id', true)
                OR (
                    current_setting('app.allow_instance_lookup', true) = 'true'
                    AND instance_name = current_setting('app.current_instance_name', true)
                )
            )
        """
    )
    op.execute(
        """
        CREATE POLICY evolution_instances_write ON evolution_instances
            FOR ALL
            USING (tenant_id::text = current_setting('app.current_tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true))
        """
    )


def upgrade() -> None:
    _drop_ventas_usuario_not_null()
    _add_unique_pair_constraints()
    _clean_orphaned_productos_categoria()
    _clean_orphaned_leads_asignado()
    _clean_orphaned_ventas()
    _clean_orphaned_revision_humana()
    _clean_orphaned_ai_conversations()
    _clean_orphaned_sessions()
    _clean_orphaned_sales_targets()
    _clean_orphaned_smart_alerts()
    _add_composite_foreign_keys()
    _update_evolution_instances_rls()
    _encrypt_legacy_llm_keys()


def downgrade() -> None:
    raise NotImplementedError("Forward-only migration")
