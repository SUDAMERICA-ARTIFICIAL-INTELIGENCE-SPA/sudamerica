"""AI Orchestrator — builds business context (the WHAT) and generates via open_agent (the HOW).

api_execute owns: system prompt, knowledge, product catalog, intent → context mapping,
conversation history and persistence, and all post-processing.
open_agent (mode `generate`) owns: a single stateless LLM call, without tools.
"""

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ApiExecuteSettings
from app.services.prompt_sections import (
    WHATSAPP_FORMAT_RULES,
    _append_prompt_section,
    _format_customer_lines,
    build_catalog_text,
    compose_system_prompt,
    welcome_rules_mesa,
    welcome_rules_whatsapp,
)
from app.services.tenant_rubro import load_tenant_rubro as _load_tenant_rubro
from shared.database.session import set_tenant_context
from shared.middleware import build_service_auth_headers
from shared.rubros import RUBRO_DEFAULT, Capacidad, rubro_def
from shared.utils.http_client import internal_http

logger = logging.getLogger(__name__)

# Generic behavioral rules the customer/onboarding chat always applies. They are
# appended to `system_prompt_override` to form the final system prompt. The eval
# harness extracts this exact constant by AST, so offline evals stay in lockstep
# with production behavior.
BEHAVIORAL_RULES = """
REGLAS DE COMPORTAMIENTO (aplicar siempre):
- Si el historial de conversación muestra mensajes previos, NO saludes de nuevo. Continúa la conversación naturalmente.
- Nunca repitas la misma frase o estructura en respuestas consecutivas. Varía tus respuestas.
- No inventes información que no esté en el contexto proporcionado.
- Sé conciso y directo. Evita respuestas excesivamente largas.
- Responde en el mismo idioma que el usuario.
- Si no sabes algo, dilo honestamente en vez de inventar.
- NUNCA menciones que eres una IA o un modelo de lenguaje a menos que te pregunten directamente.
- Mantén un tono amigable y profesional.
- Si el usuario hace una pregunta que no está en tu contexto, ofrece ayudar con lo que sí conoces.
""".strip()


async def _has_mesas(session: AsyncSession, tenant_id: UUID) -> bool:
    """Check if tenant has any active mesas configured.

    Runs on the caller's already tenant-scoped request session to avoid an
    extra connection checkout. The query filters by tenant_id explicitly.
    """
    try:
        result = await session.execute(
            sql_text("SELECT 1 FROM mesas WHERE tenant_id = :tid AND activo = true LIMIT 1"),
            {"tid": str(tenant_id)},
        )
        return result.scalar_one_or_none() is not None
    except Exception:
        logger.warning("Could not check mesas for tenant %s", tenant_id, exc_info=True)
        return False



# ── Data loaders (read from shared DB) ───────────────────────────────

async def _load_agent_config(session: AsyncSession, tenant_id: UUID) -> dict | None:
    """Load system prompt and config from agente_config table (tenant-level, one per restaurant)."""
    result = await session.execute(
        sql_text(
            "SELECT system_prompt, modelo, temperatura, max_tokens, "
            "umbral_confianza, instrucciones_disponibilidad, menu_pdf_url, "
            "menu_cabecera_url, "
            "COALESCE(tiempo_estimado_preparacion, 30) AS tiempo_estimado_preparacion "
            "FROM agente_config WHERE tenant_id = :tid AND activo = true "
            "ORDER BY created_at LIMIT 1"
        ),
        {"tid": str(tenant_id)},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def _load_tenant_name(session: AsyncSession, tenant_id: UUID) -> str:
    """Get tenant name for default prompt generation."""
    result = await session.execute(
        sql_text("SELECT nombre FROM tenants WHERE id = :tid"),
        {"tid": str(tenant_id)},
    )
    return result.scalar_one_or_none() or "tu negocio"


async def _load_knowledge_context(session: AsyncSession, tenant_id: UUID) -> str:
    """Load and format all active knowledge entries."""
    result = await session.execute(
        sql_text(
            "SELECT type, title, content FROM tenant_knowledge "
            "WHERE tenant_id = :tid AND activo = true "
            "ORDER BY priority DESC, created_at ASC"
        ),
        {"tid": str(tenant_id)},
    )
    rows = result.mappings().all()
    if not rows:
        return ""
    sections = [f"[{r['type']}] {r['title']}:\n{r['content']}" for r in rows]
    return "\n---\n".join(sections)


async def _fetch_modifier_map(session: AsyncSession, tenant_id: UUID) -> dict[str, list[dict]]:
    """Load all product modifiers in a single query. Graceful if tables missing."""
    modifier_map: dict[str, list[dict]] = {}
    try:
        mod_result = await session.execute(
            sql_text(
                "SELECT mg.id AS group_id, mg.nombre AS group_nombre, mg.tipo, mg.obligatorio, "
                "m.id AS mod_id, m.nombre AS mod_nombre, m.precio_delta, pmg.producto_id "
                "FROM producto_modifier_groups pmg "
                "JOIN modifier_groups mg ON mg.id = pmg.modifier_group_id AND mg.activo = true "
                "AND mg.tenant_id = :tid "
                "JOIN modifiers m ON m.grupo_id = mg.id AND m.activo = true "
                "ORDER BY mg.nombre, m.nombre"
            ),
            {"tid": str(tenant_id)},
        )
        for row in mod_result.mappings().all():
            pid = str(row["producto_id"])
            modifier_map.setdefault(pid, []).append(dict(row))
    except ImportError:
        logger.debug("Modifier tables not available, skipping modifiers")
    except Exception:
        logger.error("Failed to load modifiers for tenant %s", tenant_id, exc_info=True)
    return modifier_map


async def _load_missing_ingredients(session: AsyncSession, tenant_id: UUID) -> dict[str, list[str]]:
    """Load map of producto_id → missing ingredient names."""
    try:
        from app.services.suministro_svc import get_unavailable_ingredients
        return await get_unavailable_ingredients(session, tenant_id)
    except ImportError:
        return {}
    except Exception:
        logger.warning("Failed to load missing ingredients for tenant %s", tenant_id, exc_info=True)
        return {}


async def _load_product_catalog_with_images(
    session: AsyncSession, tenant_id: UUID, sucursal_id: UUID | None = None,
) -> tuple[str, bool]:
    """Load all active products with modifiers, formatted for LLM consumption.

    If sucursal_id is provided, overrides prices with sucursal-specific pricing
    from sucursal_producto_precios table (per-branch pricing).
    """
    result = await session.execute(
        sql_text(
            "SELECT id, nombre, precio, descripcion, disponible, imagen_url, unidad_venta "
            "FROM productos WHERE tenant_id = :tid AND activo = true "
            "ORDER BY nombre"
        ),
        {"tid": str(tenant_id)},
    )
    products = [dict(p) for p in result.mappings().all()]
    if not products:
        return "", False

    # Override prices with sucursal-specific pricing if available
    if sucursal_id and products:
        try:
            spp_result = await session.execute(
                sql_text(
                    "SELECT producto_id, precio FROM sucursal_producto_precios "
                    "WHERE tenant_id = :tid AND sucursal_id = :sid AND activo = true"
                ),
                {"tid": str(tenant_id), "sid": str(sucursal_id)},
            )
            price_overrides = {str(r["producto_id"]): r["precio"] for r in spp_result.mappings().all()}
            if price_overrides:
                for p in products:
                    override = price_overrides.get(str(p["id"]))
                    if override is not None:
                        p["precio"] = override
                logger.debug("Applied %d sucursal price overrides", len(price_overrides))
        except Exception:
            logger.warning("Failed to load sucursal price overrides for %s", sucursal_id, exc_info=True)

    modifier_map = await _fetch_modifier_map(session, tenant_id)
    missing_ingredients = await _load_missing_ingredients(session, tenant_id)
    return build_catalog_text(products, modifier_map, missing_ingredients)


# ── System message builder ───────────────────────────────────────────

async def _build_base_system_prompt(
    session: AsyncSession,
    tenant_id: UUID,
    config: dict | None,
) -> str:
    """Return either the configured prompt or the tenant-aware fallback prompt."""
    if config and config.get("system_prompt"):
        return config["system_prompt"]

    tenant_name = await _load_tenant_name(session, tenant_id)
    return (
        f"Eres el asistente virtual de {tenant_name}. "
        "Ayudas a los clientes con consultas, pedidos, reservas y mÃ¡s. "
        "Eres amable, rÃ¡pido y profesional. Responde en espaÃ±ol."
    )



async def _load_delivery_config(session: AsyncSession, tenant_id: UUID, sucursal_id: UUID | None = None) -> str:
    """Load delivery cost info for the prompt. If sucursal_id known, use that; else list all."""
    if sucursal_id:
        result = await session.execute(
            sql_text(
                "SELECT nombre, costo_delivery, zona_delivery FROM sucursales "
                "WHERE id = :sid AND tenant_id = :tid AND activo = true"
            ),
            {"sid": str(sucursal_id), "tid": str(tenant_id)},
        )
        row = result.mappings().first()
        if row and row["costo_delivery"]:
            zone = f" Zona: {row['zona_delivery']}." if row.get("zona_delivery") else ""
            return f"COSTO DE DELIVERY: ${row['costo_delivery']} para {row['nombre']}.{zone}"
        return ""
    # Multi-sucursal: list all delivery costs
    result = await session.execute(
        sql_text(
            "SELECT nombre, costo_delivery, zona_delivery FROM sucursales "
            "WHERE tenant_id = :tid AND activo = true AND costo_delivery > 0 "
            "ORDER BY es_principal DESC"
        ),
        {"tid": str(tenant_id)},
    )
    rows = result.mappings().all()
    if not rows:
        return ""
    lines = ["COSTOS DE DELIVERY POR SUCURSAL:"]
    for r in rows:
        zone = f" (zona: {r['zona_delivery']})" if r.get("zona_delivery") else ""
        lines.append(f"- {r['nombre']}: ${r['costo_delivery']}{zone}")
    return "\n".join(lines)


async def _load_customer_context(
    session: AsyncSession, tenant_id: UUID, lead_id: UUID, rubro_key: str,
) -> str:
    """Load customer history for personalized AI responses."""
    try:
        result = await session.execute(
            sql_text(
                "SELECT nombre, estado_cliente, total_pedidos, total_gastado, "
                "plato_favorito, ultima_visita, frecuencia_dias "
                "FROM leads WHERE id = :lid AND tenant_id = :tid AND activo = true"
            ),
            {"lid": str(lead_id), "tid": str(tenant_id)},
        )
        row = result.mappings().first()
        if not row or not row.get("total_pedidos"):
            return ""
        return "\n".join(_format_customer_lines(row, rubro_key))
    except Exception:
        logger.warning("Could not load customer context for lead %s", lead_id, exc_info=True)
        return ""


async def build_system_message(
    session: AsyncSession,
    tenant_id: UUID,
    settings=None,
    lead_id: UUID | None = None,
    sucursal_id: UUID | None = None,
) -> tuple[str, dict | None]:
    """Build the complete system message with all business context.

    Returns (system_message, agent_config_dict).

    Layers:
    1. Base prompt (from agente_config or auto-generated, sucursal-specific if available)
    2. Knowledge context (from tenant_knowledge)
    3. Product catalog + cotizador rules (with sucursal-specific pricing if applicable)
    4. Media capability rules (if tenant has menu PDF or product images)
    5. Customer context (if lead_id provided — personalizes response for returning customers)
    """
    config = await _load_agent_config(session, tenant_id)
    system_prompt = await _build_base_system_prompt(session, tenant_id, config)

    # Rubro del tenant (fail-safe restaurante). La composición (glosario solo para
    # rubros no-restaurante, gates de módulos) vive en prompt_sections.compose_system_prompt,
    # compartida con el harness de evals: mismo código = mismo prompt.
    rubro_key = await _load_tenant_rubro(session, tenant_id)
    rubro = rubro_def(rubro_key)

    knowledge = await _load_knowledge_context(session, tenant_id)
    catalog, has_images = await _load_product_catalog_with_images(
        session, tenant_id, sucursal_id=sucursal_id,
    )
    has_mesas = rubro.tiene_capacidad(Capacidad.AGENDA) and await _has_mesas(session, tenant_id)
    delivery_config = (
        await _load_delivery_config(session, tenant_id, sucursal_id=sucursal_id)
        if rubro.tiene_capacidad(Capacidad.DELIVERY)
        else ""
    )
    customer_ctx = ""
    if lead_id:
        customer_ctx = await _load_customer_context(session, tenant_id, lead_id, rubro_key)

    system_prompt = compose_system_prompt(
        system_prompt,
        rubro_key=rubro_key,
        knowledge=knowledge,
        catalog=catalog,
        has_images=has_images,
        config=config,
        has_mesas=has_mesas,
        delivery_config=delivery_config,
        customer_context=customer_ctx,
    )
    return system_prompt, config


# ── Mesa QR context ───────────────────────────────────────────────────

import re

_MESA_TOKEN_RE = re.compile(r"\[mesa:([a-f0-9]{32})\]", re.IGNORECASE)


def _extract_mesa_token(message: str) -> tuple[str, str | None]:
    """Extract [mesa:<token>] from message. Returns (cleaned_message, token_or_None)."""
    match = _MESA_TOKEN_RE.search(message)
    if not match:
        return message, None
    token = match.group(1)
    cleaned = _MESA_TOKEN_RE.sub("", message).strip()
    return cleaned, token


async def _load_mesa_context(session: AsyncSession, tenant_id: UUID, qr_token: str) -> dict | None:
    """Load mesa + sucursal info by QR token for prompt injection."""
    result = await session.execute(
        sql_text(
            "SELECT m.id, m.numero, m.nombre, m.sucursal_id, "
            "s.nombre AS sucursal_nombre "
            "FROM mesas m "
            "LEFT JOIN sucursales s ON s.id = m.sucursal_id "
            "WHERE m.qr_token = :token AND m.tenant_id = :tid AND m.activo = true"
        ),
        {"token": qr_token, "tid": str(tenant_id)},
    )
    row = result.mappings().first()
    return dict(row) if row else None


def _build_mesa_prompt_section(mesa: dict, rubro_key: str = RUBRO_DEFAULT) -> str:
    """Build the mesa context section for the system prompt (welcome gateado por rubro)."""
    sucursal = mesa.get("sucursal_nombre") or ""
    location = f" de {sucursal}" if sucursal else ""
    return (
        f"CONTEXTO DE MESA:\n"
        f"- El cliente esta en MESA #{mesa['numero']}{location}.\n"
        f"- Tipo de entrega: MESA (no preguntar).\n"
        f"- Al confirmar pedido, usar tipo_entrega=\"MESA\", numero_mesa={mesa['numero']}.\n\n"
        + welcome_rules_mesa(rubro_key)
    )


# ── Media marker extraction (post-processing) ────────────────────────

_MENU_MARKER_RE = re.compile(r"\s*\[ENVIAR[_ ]?MENU[_ ]?(?:PDF)?\]\s*", re.IGNORECASE)
_IMAGE_MARKER_RE = re.compile(r"\s*\[ENVIAR[_ ]?IMAGEN:([^\]]+)\]\s*", re.IGNORECASE)
# Interactive message markers: [ENVIAR_POLL:pregunta|opcion1|opcion2|...]
_POLL_MARKER_RE = re.compile(r"\s*\[ENVIAR[_ ]?POLL:([^\]]+)\]\s*", re.IGNORECASE)
# [ENVIAR_LISTA:titulo|boton|seccion1:fila1,fila2|seccion2:fila3,fila4]
_LIST_MARKER_RE = re.compile(r"\s*\[ENVIAR[_ ]?LISTA:([^\]]+)\]\s*", re.IGNORECASE)
# Catch-all: strip ANY remaining [ENVIAR_*] markers the AI might invent
_CATCHALL_MARKER_RE = re.compile(r"\s*\[ENVIAR[^\]]*\]\s*", re.IGNORECASE)
# Mesa action markers (waiter call / request bill)
_ALERTA_MESERO_RE = re.compile(r"\s*\[ALERTA[_ ]?MESERO\]\s*", re.IGNORECASE)
_PEDIR_CUENTA_RE = re.compile(r"\s*\[PEDIR[_ ]?CUENTA\]\s*", re.IGNORECASE)

# User intent detection for menu requests (language-agnostic keywords)
_MENU_REQUEST_RE = re.compile(
    r"(?:menu|menú|carta|pdf|ver\s+(?:los\s+)?(?:platos|productos|precios)"
    r"|mandar?\s+(?:el\s+)?(?:menu|menú|carta)"
    r"|enviar?\s+(?:el\s+)?(?:menu|menú|carta)"
    r"|(?:tienes?|tienen?)\s+(?:el\s+)?(?:menu|menú|carta))",
    re.IGNORECASE,
)


async def _resolve_menu_url(cfg: dict, tenant_id: UUID, settings) -> str | None:
    """Single source for the menu PDF URL fallback chain:
    configured menu_pdf_url → latest confirmed uploaded menu → auto-generated.
    """
    menu_url = cfg.get("menu_pdf_url")
    if not menu_url:
        menu_url = await _get_uploaded_menu_url(tenant_id, settings)
    if not menu_url:
        menu_url = await _auto_generate_menu_pdf(None, tenant_id, settings)
    return menu_url


async def _attach_menu(
    text: str, config: dict | None, tenant_id: UUID, settings,
) -> tuple[str, list[dict]]:
    """Resolve [ENVIAR_MENU] marker.

    Returns cleaned text and a list of attachments.  When the tenant has
    a ``menu_cabecera_url`` configured, the header image is returned
    first so it is sent *before* the PDF — giving the customer a visual
    preview of the menu in the WhatsApp chat.
    """
    if not _MENU_MARKER_RE.search(text):
        return text, []
    cfg = config or {}
    menu_url = await _resolve_menu_url(cfg, tenant_id, settings)
    text = _MENU_MARKER_RE.sub("", text)
    if not menu_url:
        return text, []

    attachments: list[dict] = []
    # Header image sent first (preview / branding)
    cabecera_url = cfg.get("menu_cabecera_url")
    if cabecera_url:
        attachments.append({
            "url": cabecera_url,
            "type": "image",
            "file_name": "menu-cabecera.jpg",
            "caption": cfg.get("_tenant_name", "Nuestro Menu"),
        })
    # Then the PDF document
    attachments.append({"url": menu_url, "type": "document", "file_name": "Menu.pdf"})
    return text, attachments


async def _attach_image(text: str, tenant_id: UUID, settings) -> tuple[str, dict | None]:
    """Resolve [ENVIAR_IMAGEN:nombre] marker.

    Returns cleaned text and an attachment dict with the image URL plus a
    formatted caption containing the product name, price and description.
    """
    match = _IMAGE_MARKER_RE.search(text)
    if not match:
        return text, None
    product_name = match.group(1).strip()
    product = await _find_product_image(tenant_id, product_name, settings)
    text = _IMAGE_MARKER_RE.sub("", text)
    if not product or not product.get("imagen_url"):
        return text, None

    # Build caption: *Nombre* - $precio\nDescripcion
    nombre = product.get("nombre", product_name)
    precio = product.get("precio")
    descripcion = (product.get("descripcion") or "").strip()
    caption_parts = [f"*{nombre}*"]
    if precio is not None:
        try:
            precio_num = float(precio)
            caption_parts.append(f"${precio_num:,.0f}".replace(",", "."))
        except (TypeError, ValueError):
            caption_parts.append(f"${precio}")
    header = " — ".join(caption_parts)
    caption = header
    if descripcion:
        caption += f"\n{descripcion}"

    return text, {
        "url": product["imagen_url"],
        "type": "image",
        "file_name": f"{nombre}.jpg",
        "caption": caption,
    }


def _extract_poll(text: str) -> tuple[str, dict | None]:
    """Extract [ENVIAR_POLL:pregunta|opcion1|opcion2|...] marker.

    Returns cleaned text and poll dict or None.
    """
    match = _POLL_MARKER_RE.search(text)
    if not match:
        return text, None
    parts = [p.strip() for p in match.group(1).split("|") if p.strip()]
    if len(parts) < 3:  # need question + at least 2 options
        text = _POLL_MARKER_RE.sub("", text)
        return text, None
    question = parts[0]
    options = parts[1:]
    text = _POLL_MARKER_RE.sub("", text)
    return text, {"type": "poll", "question": question, "options": options}


def _extract_list(text: str) -> tuple[str, dict | None]:
    """Extract [ENVIAR_LISTA:titulo|boton|seccion:fila1,fila2|...] marker.

    Returns cleaned text and list dict or None.
    """
    match = _LIST_MARKER_RE.search(text)
    if not match:
        return text, None
    parts = [p.strip() for p in match.group(1).split("|") if p.strip()]
    if len(parts) < 3:  # need title + button + at least 1 section
        text = _LIST_MARKER_RE.sub("", text)
        return text, None
    title = parts[0]
    button_text = parts[1]
    sections = []
    for part in parts[2:]:
        if ":" in part:
            sec_title, rows_str = part.split(":", 1)
            rows = [
                {"title": r.strip(), "description": "", "rowId": r.strip().lower().replace(" ", "_")}
                for r in rows_str.split(",") if r.strip()
            ]
        else:
            sec_title = ""
            rows = [{"title": part, "description": "", "rowId": part.lower().replace(" ", "_")}]
        sections.append({"title": sec_title.strip(), "rows": rows})
    text = _LIST_MARKER_RE.sub("", text)
    return text, {"type": "list", "title": title, "button_text": button_text, "sections": sections}


async def _resolve_media_markers(
    text: str,
    config: dict | None,
    tenant_id: UUID,
    settings=None,
) -> tuple[str, list[dict]]:
    """Detect and resolve media markers in AI response."""
    attachments: list[dict] = []

    text, menu_items = await _attach_menu(text, config, tenant_id, settings)
    attachments.extend(menu_items)

    text, image = await _attach_image(text, tenant_id, settings)
    if image:
        attachments.append(image)

    text, poll = _extract_poll(text)
    if poll:
        attachments.append(poll)

    text, walist = _extract_list(text)
    if walist:
        attachments.append(walist)

    # Mesa action markers
    if _ALERTA_MESERO_RE.search(text):
        text = _ALERTA_MESERO_RE.sub("", text)
        attachments.append({"type": "mesa_action", "action": "llamar_mesero"})
        logger.info("Mesa action: llamar_mesero")
    if _PEDIR_CUENTA_RE.search(text):
        text = _PEDIR_CUENTA_RE.sub("", text)
        attachments.append({"type": "mesa_action", "action": "pedir_cuenta"})
        logger.info("Mesa action: pedir_cuenta")

    text = _CATCHALL_MARKER_RE.sub("", text)
    return text.strip(), attachments


# ── Cached fresh DB session factory (avoids creating engine per call) ──

_postprocess_engine = None
_postprocess_factory = None


def _get_postprocess_factory(settings):
    """Lazy-init a shared engine+factory for post-processing DB operations."""
    global _postprocess_engine, _postprocess_factory
    if _postprocess_factory is not None:
        return _postprocess_factory
    from shared.database import create_engine, create_session_factory
    db_url = getattr(settings, "DATABASE_URL", "")
    _postprocess_engine = create_engine(db_url, pool_size=3, max_overflow=2)
    _postprocess_factory = create_session_factory(_postprocess_engine)
    return _postprocess_factory


async def _auto_generate_menu_pdf(
    session: AsyncSession,
    tenant_id: UUID,
    settings=None,
) -> str | None:
    """Auto-generate a menu PDF from the product catalog and upload to GCS."""
    try:
        from app.services.menu_pdf_service import generate_menu_pdf
        from shared.database.session import set_tenant_context

        bucket = getattr(settings, "GCS_BUCKET_NAME", "sudamerica-media")
        factory = _get_postprocess_factory(settings)
        async with factory() as fresh_session:
            await set_tenant_context(fresh_session, str(tenant_id))
            url = await generate_menu_pdf(fresh_session, tenant_id, bucket)
            if url:
                logger.info("Auto-generated menu PDF for tenant %s", tenant_id)
            return url
    except Exception:
        logger.exception("Failed to auto-generate menu PDF for tenant %s", tenant_id)
        return None


async def _get_uploaded_menu_url(
    tenant_id: UUID,
    settings=None,
) -> str | None:
    """Return a fresh signed URL for the tenant's most recently confirmed
    uploaded menu PDF, or None if they never uploaded one.

    Fixes the case where the tenant uploaded a menu but never checked
    ``set_as_official_pdf`` at import time, so ``agente_config.menu_pdf_url``
    stayed empty and the agent fell back to auto-generating a PDF from
    the catalog instead of sending the uploaded file.
    """
    try:
        from app.models.menu_import import MenuImport
        from shared.database.session import set_tenant_context
        from shared.utils.storage import generate_signed_url
        from sqlalchemy import select

        bucket = getattr(settings, "GCS_BUCKET_NAME", None)
        factory = _get_postprocess_factory(settings)
        async with factory() as fresh_session:
            await set_tenant_context(fresh_session, str(tenant_id))
            stmt = (
                select(MenuImport)
                .where(
                    MenuImport.tenant_id == tenant_id,
                    MenuImport.status == "CONFIRMED",
                    MenuImport.original_pdf_path.is_not(None),
                )
                .order_by(MenuImport.version.desc())
                .limit(1)
            )
            row = (await fresh_session.execute(stmt)).scalar_one_or_none()
            if row is None or not row.original_pdf_path or not bucket:
                return None
            # Regenerate signed URL (stored one may have expired)
            return generate_signed_url(bucket, row.original_pdf_path)
    except Exception:
        logger.exception("Failed to fetch uploaded menu for tenant %s", tenant_id)
        return None


async def _find_product_image(
    tenant_id: UUID,
    product_name: str,
    settings=None,
) -> dict | None:
    """Find a product's imagen_url + price + description by fuzzy name match.

    Returns a dict with {imagen_url, nombre, precio, descripcion} or None.
    Uses exact match first, then falls back to ILIKE partial match.
    """
    try:
        from shared.database.session import set_tenant_context

        factory = _get_postprocess_factory(settings)
        async with factory() as fresh_session:
            await set_tenant_context(fresh_session, str(tenant_id))

            # 1. Exact match
            result = await fresh_session.execute(
                sql_text(
                    "SELECT imagen_url, nombre, precio, descripcion FROM productos "
                    "WHERE tenant_id = :tid AND activo = true "
                    "AND LOWER(nombre) = LOWER(:name) AND imagen_url IS NOT NULL "
                    "LIMIT 1"
                ),
                {"tid": str(tenant_id), "name": product_name},
            )
            row = result.mappings().first()
            if row:
                return dict(row)

            # 2. Partial match (contains)
            result = await fresh_session.execute(
                sql_text(
                    "SELECT imagen_url, nombre, precio, descripcion FROM productos "
                    "WHERE tenant_id = :tid AND activo = true "
                    "AND nombre ILIKE :pattern AND imagen_url IS NOT NULL "
                    "ORDER BY LENGTH(nombre) ASC LIMIT 1"
                ),
                {"tid": str(tenant_id), "pattern": f"%{product_name}%"},
            )
            row = result.mappings().first()
            if row:
                return dict(row)

            return None
    except Exception:
        logger.warning("Failed to find product image for %s", product_name, exc_info=True)
        return None


# ── Order JSON extraction (post-processing) ──────────────────────────

_JSON_BLOCK_RE = re.compile(r"\s*```json\s*\n?.*?\n?\s*```\s*", re.DOTALL)


def _strip_json_block(text: str) -> str:
    """Remove ALL ```json ... ``` blocks from text so they aren't sent to the customer."""
    if "```json" not in text:
        return text
    return _JSON_BLOCK_RE.sub("", text).strip()


def extract_order_json(text: str) -> dict | None:
    """Extract confirmed order JSON from LLM response."""
    if "```json" not in text:
        return None
    try:
        json_start = text.index("```json") + 7
        json_end = text.index("```", json_start)
        json_str = text[json_start:json_end].strip()
        data = json.loads(json_str)
        if data.get("pedido_confirmado"):
            return data
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("Failed to parse order JSON: %s", exc)
    return None


async def _resolve_default_sucursal(tenant_id: UUID, settings=None) -> str | None:
    """Find the principal (or any active) sucursal for a tenant."""
    try:
        factory = _get_postprocess_factory(settings)
        async with factory() as session:
            result = await session.execute(
                sql_text(
                    "SELECT id FROM sucursales "
                    "WHERE tenant_id = :tid AND activo = true "
                    "ORDER BY es_principal DESC LIMIT 1"
                ),
                {"tid": str(tenant_id)},
            )
            row = result.scalar_one_or_none()
            return str(row) if row else None
    except Exception:
        logger.warning("Could not resolve default sucursal for tenant %s", tenant_id, exc_info=True)
        return None


async def _notify_delivery_drivers(
    tenant_id: UUID, comanda_id: UUID, order_data: dict, settings=None,
) -> None:
    """Send delivery order details to the sucursal's repartidores WhatsApp group."""
    try:
        sucursal_id = order_data.get("sucursal_id")
        if not sucursal_id:
            sucursal_id = await _resolve_default_sucursal(tenant_id, settings)
            if not sucursal_id:
                logger.debug("No sucursal found for delivery notification, tenant %s", tenant_id)
                return

        factory = _get_postprocess_factory(settings)
        async with factory() as fresh_session:
            # Load sucursal + driver group + prep time
            result = await fresh_session.execute(
                sql_text(
                    "SELECT s.grupo_repartidores_jid, s.nombre, "
                    "COALESCE(ac.tiempo_estimado_preparacion, 30) AS prep_time "
                    "FROM sucursales s "
                    "LEFT JOIN agente_config ac ON ac.tenant_id = s.tenant_id AND ac.activo = true "
                    "WHERE s.id = :sid AND s.grupo_repartidores_jid IS NOT NULL"
                ),
                {"sid": str(sucursal_id)},
            )
            row = result.mappings().first()
            if not row:
                logger.debug("No driver group configured for sucursal %s", sucursal_id)
                return

            # Resolve product names from UUIDs
            product_ids = [
                it.get("producto_id") for it in order_data.get("items", [])
                if it.get("producto_id")
            ]
            product_names: dict[str, str] = {}
            if product_ids:
                prod_result = await fresh_session.execute(
                    sql_text(
                        "SELECT id::text, nombre FROM productos WHERE id::text = ANY(:ids)"
                    ),
                    {"ids": product_ids},
                )
                product_names = {r.id: r.nombre for r in prod_result}

        direccion = order_data.get("direccion_entrega", "No especificada")
        metodo = order_data.get("metodo_pago", "No especificado")
        prep_time = row["prep_time"]
        comanda_short = str(comanda_id)[:8]

        items_text = "\n".join(
            f"  - {it.get('cantidad', 1)}x "
            f"{product_names.get(it.get('producto_id', ''), it.get('producto_id', '?'))}"
            for it in order_data.get("items", [])
        )
        msg = (
            f"*NUEVO PEDIDO DELIVERY* (#{comanda_short})\n"
            f"Sucursal: {row['nombre']}\n"
            f"Preparacion estimada: ~{prep_time} min\n"
            f"Direccion: {direccion}\n"
            f"Pago: {metodo}\n"
            f"Items:\n{items_text}\n\n"
            f"Responde *TOMO* para asignarte esta entrega."
        )

        canales_url = getattr(settings, "SERVICE_CANALES_URL", "http://localhost:8004")
        headers = build_service_auth_headers(
            service_name="api_execute", audience="canales_service",
            tenant_id=tenant_id,
            secret_key=getattr(settings, "INTERNAL_SERVICE_SECRET_KEY", ""),
            algorithm=getattr(settings, "JWT_ALGORITHM", "HS256"),
            scopes=("whatsapp:send",),
            expires_in_seconds=getattr(settings, "INTERNAL_SERVICE_TOKEN_TTL_SECONDS", 300),
        )
        headers["X-Tenant-ID"] = str(tenant_id)
        await internal_http.post(
            f"{canales_url}/api/v1/canales/whatsapp/send",
            json={
                "to": row["grupo_repartidores_jid"],
                "message": msg,
                "tenant_id": str(tenant_id),
            },
            headers=headers,
            timeout=15.0,
        )
        logger.info("Delivery notification sent to driver group %s", row["grupo_repartidores_jid"])
    except Exception:
        logger.warning("Failed to notify delivery drivers", exc_info=True)


async def _create_comanda_from_order(
    tenant_id: UUID,
    lead_id: UUID | None,
    order_data: dict,
    settings=None,
) -> bool:
    """Create a comanda directly in the DB from confirmed order JSON.

    Uses a fresh DB session to avoid transaction contamination from the caller.
    """
    try:
        from app.services.comanda_svc import create_comanda
        from shared.database.session import set_tenant_context

        comanda_data = {
            "cliente_id": str(lead_id) if lead_id else None,
            "tipo_entrega": order_data.get("tipo_entrega", "RETIRO"),
            "numero_mesa": order_data.get("numero_mesa"),
            "canal_origen": "WHATSAPP",
            "items": order_data.get("items", []),
        }
        # Delivery fields
        if order_data.get("tipo_entrega") == "DELIVERY":
            comanda_data["direccion_entrega"] = order_data.get("direccion_entrega")
            comanda_data["ubicacion_lat"] = order_data.get("ubicacion_lat")
            comanda_data["ubicacion_lng"] = order_data.get("ubicacion_lng")
            comanda_data["metodo_pago"] = order_data.get("metodo_pago")
            comanda_data["pago_confirmado"] = order_data.get("pago_confirmado", False)
            comanda_data["costo_delivery"] = order_data.get("costo_delivery", 0)
        # Sucursal from mesa context or order data; resolve default for delivery
        sucursal_id = order_data.get("sucursal_id")
        if not sucursal_id and order_data.get("tipo_entrega") == "DELIVERY":
            sucursal_id = await _resolve_default_sucursal(tenant_id, settings)
        if sucursal_id:
            comanda_data["sucursal_id"] = sucursal_id
            order_data["sucursal_id"] = sucursal_id  # propagate for notification

        logger.info(
            "Creating comanda: tipo=%s, items=%d, lead=%s",
            comanda_data["tipo_entrega"],
            len(comanda_data["items"]),
            lead_id,
        )

        factory = _get_postprocess_factory(settings)
        async with factory() as fresh_session:
            await set_tenant_context(fresh_session, str(tenant_id))
            comanda = await create_comanda(fresh_session, tenant_id, comanda_data)

            # Create delivery assignment for DELIVERY orders
            if order_data.get("tipo_entrega") == "DELIVERY":
                from app.services.delivery_svc import create_assignment
                await create_assignment(
                    fresh_session,
                    tenant_id,
                    comanda.id,
                    metodo_pago=order_data.get("metodo_pago"),
                    monto_a_cobrar=float(order_data.get("costo_delivery", 0)),
                )

            await fresh_session.commit()
            logger.info("Comanda auto-created: id=%s, tenant=%s", comanda.id, tenant_id)

            # Notify delivery drivers if DELIVERY
            if order_data.get("tipo_entrega") == "DELIVERY":
                import asyncio
                task = asyncio.create_task(
                    _notify_delivery_drivers(tenant_id, comanda.id, order_data, settings)
                )
                task.add_done_callback(lambda t: t.exception() if not t.cancelled() and t.exception() else None)

            return True
    except Exception as exc:
        logger.error(
            "Failed to auto-create comanda for tenant %s: %s",
            tenant_id, exc, exc_info=True,
        )
        return False


# ── Orchestrator helpers ─────────────────────────────────────────────


async def _load_customer_history(
    session: AsyncSession,
    tenant_id: UUID,
    lead_id: UUID | None,
    canal: str,
    limit: int = 10,
) -> list[dict[str, str]]:
    """Load recent customer conversation history for this lead + canal.

    Mirror of `sudamerica_orchestrator._load_sudamerica_history`, but filtered by
    `lead_id` + `canal` (the customer discriminators) instead of `usuario_id`.
    """
    if lead_id is None:
        return []
    result = await session.execute(
        sql_text(
            "SELECT role, content FROM ai_conversations "
            "WHERE tenant_id = :tid AND lead_id = :lid AND canal = :canal "
            "ORDER BY created_at DESC LIMIT :lim"
        ),
        {"tid": str(tenant_id), "lid": str(lead_id), "canal": canal, "lim": limit},
    )
    rows = [{"role": r["role"], "content": r["content"]} for r in result.mappings().all()]
    rows.reverse()
    return rows


async def _save_customer_message(
    session: AsyncSession,
    tenant_id: UUID,
    lead_id: UUID | None,
    session_id: UUID | None,
    canal: str,
    *,
    role: str,
    content: str,
    tokens: int | None,
    modelo: str | None,
    status: str,
    media_url: str | None = None,
    media_type: str | None = None,
) -> UUID:
    """Persist one customer conversation message and return its new id.

    Persistence for the orchestrated customer chat. The caller must have set the
    RLS tenant context on `session` beforehand.
    """
    result = await session.execute(
        sql_text(
            "INSERT INTO ai_conversations "
            "(tenant_id, lead_id, session_id, role, content, tokens_used, "
            "modelo, canal, status, media_url, media_type) "
            "VALUES (:tid, :lid, :sid, :role, :content, :tokens, "
            ":modelo, :canal, :status, :media_url, :media_type) "
            "RETURNING id"
        ),
        {
            "tid": str(tenant_id),
            "lid": str(lead_id) if lead_id else None,
            "sid": str(session_id) if session_id else None,
            "role": role,
            "content": content,
            "tokens": tokens,
            "modelo": modelo,
            "canal": canal,
            "status": status,
            "media_url": media_url,
            "media_type": media_type,
        },
    )
    return result.scalar_one()


async def load_agent_flags(session: AsyncSession, tenant_id: UUID) -> dict:
    """Load the tenant's auto-response + debounce flags from agente_config.

    Backs ``GET /ai/config`` for canales_service. Returns the column defaults
    when no active config row exists, so the caller always gets a usable shape.
    """
    result = await session.execute(
        sql_text(
            "SELECT auto_respuesta_whatsapp, debounce_seconds "
            "FROM agente_config WHERE tenant_id = :tid AND activo = true "
            "ORDER BY created_at LIMIT 1"
        ),
        {"tid": str(tenant_id)},
    )
    row = result.mappings().first()
    if row is None:
        return {"auto_respuesta_whatsapp": True, "debounce_seconds": 4.0}
    return {
        "auto_respuesta_whatsapp": bool(row["auto_respuesta_whatsapp"]),
        "debounce_seconds": float(row["debounce_seconds"]),
    }


def _import_signature(role: str, content: str, created_at) -> tuple:
    """Normalize (role, content, created_at) into a dedup signature.

    Normalizes to UTC with whole-second precision and stripped content, so a
    re-sync of the same WhatsApp history is idempotent.
    """
    ts = created_at
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts)
        except ValueError:
            ts = None
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ts = ts.astimezone(timezone.utc).replace(microsecond=0)
    return role, content.strip(), ts


async def import_conversation_messages(
    session: AsyncSession,
    tenant_id: UUID,
    lead_id: UUID,
    canal: str,
    messages: list,
) -> dict:
    """Persist historical customer messages idempotently for a lead + canal.

    Backs ``POST /ai/conversations/import``. Deduplicates against rows already
    stored for the lead + canal (by normalized signature) and preserves original
    timestamps. The caller must set the RLS tenant context beforehand.
    """
    if not messages:
        return {"lead_id": str(lead_id), "imported_count": 0, "skipped_count": 0}

    lead_ok = await session.execute(
        sql_text("SELECT 1 FROM leads WHERE tenant_id = :tid AND id = :lid"),
        {"tid": str(tenant_id), "lid": str(lead_id)},
    )
    if lead_ok.scalar_one_or_none() is None:
        return {"lead_id": str(lead_id), "imported_count": 0, "skipped_count": len(messages)}

    existing = await session.execute(
        sql_text(
            "SELECT role, content, created_at FROM ai_conversations "
            "WHERE tenant_id = :tid AND lead_id = :lid AND canal = :canal"
        ),
        {"tid": str(tenant_id), "lid": str(lead_id), "canal": canal},
    )
    seen = {
        _import_signature(r["role"], r["content"], r["created_at"])
        for r in existing.mappings().all()
    }

    imported = 0
    for m in messages:
        signature = _import_signature(m.role, m.content, m.created_at)
        if signature in seen:
            continue
        await session.execute(
            sql_text(
                "INSERT INTO ai_conversations "
                "(tenant_id, lead_id, role, content, canal, status, "
                "media_url, media_type, created_at) "
                "VALUES (:tid, :lid, :role, :content, :canal, :status, "
                ":media_url, :media_type, "
                "COALESCE(CAST(:created_at AS timestamptz), now()))"
            ),
            {
                "tid": str(tenant_id),
                "lid": str(lead_id),
                "role": m.role,
                "content": m.content,
                "canal": canal,
                "status": "SENT",
                "media_url": m.media_url,
                "media_type": m.media_type,
                "created_at": m.created_at,
            },
        )
        seen.add(signature)
        imported += 1

    if imported:
        await session.commit()
    return {
        "lead_id": str(lead_id),
        "imported_count": imported,
        "skipped_count": len(messages) - imported,
    }


async def _try_create_comanda(
    response_text: str, tenant_id: UUID, lead_id: UUID | None, settings,
) -> bool:
    """Extract order JSON and create comanda if confirmed. Returns True if created."""
    order_data = extract_order_json(response_text)
    if not order_data:
        return False
    if not lead_id:
        logger.warning("Order JSON detected for tenant %s but lead_id is None", tenant_id)
        return False
    logger.info(
        "Order JSON detected for tenant %s, lead %s: %d items",
        tenant_id, lead_id, len(order_data.get("items", [])),
    )
    return await _create_comanda_from_order(tenant_id, lead_id, order_data, settings=settings)


def _extract_reservation_json(text: str) -> dict | None:
    """Extract confirmed reservation JSON from LLM response."""
    if "```json" not in text:
        return None
    try:
        json_start = text.index("```json") + 7
        json_end = text.index("```", json_start)
        json_str = text[json_start:json_end].strip()
        data = json.loads(json_str)
        if data.get("reserva_confirmada"):
            return data
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("Failed to parse reservation JSON: %s", exc)
    return None


def _build_reserva_data(data: dict, lead_id: UUID | None) -> dict:
    """Build reservation data dict from extracted JSON."""
    from datetime import date as _date, time as _time
    return {
        "fecha_reserva": _date.fromisoformat(data["fecha"]),
        "hora_inicio": _time.fromisoformat(data["hora"]),
        "cantidad_personas": data["cantidad_personas"],
        "nombre_cliente": data["nombre_cliente"],
        "rut": data.get("rut"),
        "email": data.get("email"),
        "telefono": data.get("telefono"),
        "lead_id": lead_id,
        "mesa_id": data.get("mesa_id"),
    }


def _schedule_reservation_notification(
    data: dict, reserva_data: dict, settings, tenant_id: UUID,
) -> None:
    """Fire-and-forget WhatsApp notification for a confirmed reservation."""
    telefono = data.get("telefono") or reserva_data.get("telefono")
    if not telefono:
        return
    import asyncio
    from app.services.reservacion_notify import notify_reservation_confirmed
    asyncio.create_task(notify_reservation_confirmed(
        settings, tenant_id, telefono,
        data["nombre_cliente"], data["fecha"], data["hora"],
        data["cantidad_personas"],
    ))


async def _try_create_reservacion(
    response_text: str, tenant_id: UUID, lead_id: UUID | None, settings,
) -> bool:
    """Extract reservation JSON and create if confirmed."""
    data = _extract_reservation_json(response_text)
    if not data:
        return False

    logger.info("Reservation JSON detected for tenant %s: %s", tenant_id, data.get("nombre_cliente"))
    try:
        from app.services.reservacion_svc import create_reservacion
        from shared.database.session import set_tenant_context

        reserva_data = _build_reserva_data(data, lead_id)
        factory = _get_postprocess_factory(settings)
        async with factory() as fresh_session:
            await set_tenant_context(fresh_session, str(tenant_id))
            reservacion = await create_reservacion(fresh_session, tenant_id, reserva_data)
            await fresh_session.commit()
            logger.info("Reservation auto-created: %s for %s", reservacion.id, data["nombre_cliente"])
            _schedule_reservation_notification(data, reserva_data, settings, tenant_id)
            return True
    except Exception as exc:
        logger.error("Failed to auto-create reservation: %s", exc, exc_info=True)
        return False


async def _auto_attach_menu_pdf(
    message: str, config: dict | None, media_attachments: list[dict],
    tenant_id: UUID, settings,
) -> None:
    """If user asks for menu and no document is already attached, attach one."""
    if not _MENU_REQUEST_RE.search(message):
        return
    if any(a["type"] == "document" for a in media_attachments):
        return
    menu_url = await _resolve_menu_url(config or {}, tenant_id, settings)
    if menu_url:
        media_attachments.append({"url": menu_url, "type": "document", "file_name": "Menu.pdf"})
        logger.info("Menu PDF auto-attached via user intent detection")


def _apply_single_attachment(result: dict, att: dict) -> None:
    """Apply a single attachment (poll, list, or media) to the result dict.

    When a document (PDF) is sent with a preceding header image, the
    image goes into ``preview_image_url`` and the document into
    ``media_url``.  This lets the sending layer deliver the image first
    for a branded preview, then the actual file.
    """
    att_type = att.get("type")
    if att_type == "poll":
        result["poll"] = {
            "question": att["question"],
            "options": att["options"],
            "selectable_count": 1,
        }
        logger.info("Poll attachment resolved: %s", att["question"])
    elif att_type == "list":
        result["list_message"] = {
            "title": att["title"],
            "button_text": att["button_text"],
            "sections": att["sections"],
        }
        logger.info("List attachment resolved: %s", att["title"])
    elif "url" in att:
        if "media_url" not in result:
            # First media — primary slot
            result["media_url"] = att["url"]
            result["media_type"] = att_type
            result["media_file_name"] = att.get("file_name")
            if att.get("caption"):
                result["media_caption"] = att["caption"]
            logger.info("Media attachment resolved: type=%s", att_type)
        elif att_type == "document" and result.get("media_type") == "image":
            # Header image already in primary slot → move it to preview
            # and put the document in the primary slot.
            result["preview_image_url"] = result["media_url"]
            result["preview_image_caption"] = result.get("media_caption", "")
            result["media_url"] = att["url"]
            result["media_type"] = att_type
            result["media_file_name"] = att.get("file_name")
            result.pop("media_caption", None)
            logger.info("Document moved to primary, image to preview: %s", att.get("file_name"))
        else:
            logger.debug("Skipping extra media attachment: type=%s", att_type)


def _attach_first_media(result: dict, media_attachments: list[dict]) -> None:
    """Copy first media/interactive attachment into the result dict."""
    for att in media_attachments:
        _apply_single_attachment(result, att)


# ── Main orchestrator ────────────────────────────────────────────────

def _enrich_order_with_mesa(order_data: dict, mesa_context: dict) -> None:
    """Override order data with mesa context (more reliable than LLM output)."""
    order_data["tipo_entrega"] = "MESA"
    order_data["numero_mesa"] = mesa_context["numero"]
    if mesa_context.get("sucursal_id"):
        order_data["sucursal_id"] = str(mesa_context["sucursal_id"])


async def _load_tenant_sucursales(session: AsyncSession, tenant_id: UUID) -> list[dict]:
    """Load active sucursales for a tenant (for multi-branch selection)."""
    result = await session.execute(
        sql_text(
            "SELECT id, nombre, direccion FROM sucursales "
            "WHERE tenant_id = :tid AND activo = true ORDER BY es_principal DESC, nombre"
        ),
        {"tid": str(tenant_id)},
    )
    return [dict(r) for r in result.mappings().all()]


def _build_sucursal_selection_prompt(sucursales: list[dict]) -> str:
    """Build a prompt section that asks the user to choose a sucursal."""
    if len(sucursales) <= 1:
        return ""
    names = "|".join(s["nombre"] for s in sucursales)
    return (
        "SELECCION DE SUCURSAL (IMPORTANTE):\n"
        "- Este restaurante tiene varias sucursales. Si es la primera vez que el cliente "
        "escribe y no sabes a cual sucursal se refiere, preguntale usando una encuesta:\n"
        f"  [ENVIAR_POLL:¿A cuál sucursal te diriges?|{names}]\n"
        "- Una vez que el cliente elija, recuerda la sucursal para el resto de la conversacion.\n"
        "- Si el cliente ya menciono la sucursal en su mensaje, no preguntes de nuevo."
    )


async def orchestrate_chat(
    session: AsyncSession,
    tenant_id: UUID,
    message: str,
    lead_id: UUID | None,
    canal: str,
    settings: ApiExecuteSettings,
    contact_id: UUID | None = None,
    session_id: UUID | None = None,
    media_url: str | None = None,
    media_type: str | None = None,
) -> dict:
    """Orchestrate AI chat: build context, generate via open_agent, post-process."""

    # ── Location handling: WhatsApp shared location ──
    if media_type == "location" and media_url:
        try:
            parts = media_url.split(",")
            if len(parts) == 2:
                lat, lng = parts[0].strip(), parts[1].strip()
                message = f"{message} [Mi ubicacion: lat={lat}, lng={lng}]"
                logger.info("WhatsApp location received: %s, %s", lat, lng)
        except Exception:
            logger.debug("Could not parse location from media_url: %s", media_url)

    # ── Mesa QR detection: extract [mesa:token] from message ──
    clean_message, mesa_token = _extract_mesa_token(message)
    mesa_context: dict | None = None
    sucursal_id: UUID | None = None
    if mesa_token:
        mesa_context = await _load_mesa_context(session, tenant_id, mesa_token)
        if mesa_context:
            sucursal_id = mesa_context.get("sucursal_id")
            logger.info(
                "Mesa context loaded: mesa=%s, sucursal=%s, tenant=%s",
                mesa_context["numero"], sucursal_id, tenant_id,
            )

    system_message, config = await build_system_message(
        session, tenant_id, settings=settings, lead_id=lead_id,
        sucursal_id=sucursal_id,
    )

    # Rubro del tenant para gatear las reglas de bienvenida (restaurante byte-idéntico).
    rubro_key = await _load_tenant_rubro(session, tenant_id)

    # Inject mesa context or WhatsApp welcome rules into system prompt
    if mesa_context:
        system_message = _append_prompt_section(
            system_message, _build_mesa_prompt_section(mesa_context, rubro_key),
        )
    elif canal.upper() == "WHATSAPP":
        system_message = _append_prompt_section(
            system_message, welcome_rules_whatsapp(rubro_key),
        )
        # Multi-sucursal: if tenant has >1 sucursal, prompt user to choose
        sucursales = await _load_tenant_sucursales(session, tenant_id)
        sucursal_prompt = _build_sucursal_selection_prompt(sucursales)
        if sucursal_prompt:
            system_message = _append_prompt_section(system_message, sucursal_prompt)

    # Always inject WhatsApp formatting rules for WhatsApp channel
    if canal.upper() == "WHATSAPP":
        system_message = _append_prompt_section(system_message, WHATSAPP_FORMAT_RULES)

    # Append the generic behavioral rules to complete the system prompt —
    # api_execute owns the full prompt build for the orchestrated route.
    system_prompt = system_message + "\n\n" + BEHAVIORAL_RULES

    # Load recent customer history for this lead + canal.
    history = await _load_customer_history(session, tenant_id, lead_id, canal)

    # Persist the inbound user message before generating. Re-set the RLS tenant
    # context first: any prior commit on this session drops the SET LOCAL.
    await set_tenant_context(session, str(tenant_id))
    await _save_customer_message(
        session, tenant_id, lead_id, session_id, canal,
        role="user", content=clean_message, tokens=None, modelo=None,
        status="RECEIVED", media_url=media_url, media_type=media_type,
    )
    await session.commit()

    payload: dict = {
        "system_prompt": system_prompt,
        "message": clean_message,
        "history": history,
    }
    headers = build_service_auth_headers(
        service_name="api_execute",
        audience="open_agent",
        tenant_id=tenant_id,
        secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        scopes=("generate:chat",),
        expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )
    headers["X-Tenant-ID"] = str(tenant_id)

    try:
        response = await internal_http.post(
            f"{settings.SERVICE_OPEN_AGENT_URL}/api/v1/agent/generate",
            json=payload, headers=headers, timeout=60.0,
        )
        response.raise_for_status()
    except (httpx.HTTPError, RuntimeError):
        logger.exception("Failed to generate reply via open_agent")
        raise

    generate_result = response.json()
    response_text = generate_result.get("response", "")
    tokens_used = generate_result.get("tokens_used", 0)
    model_used = generate_result.get("model_used", "")

    # Persist the assistant reply (raw, with markers) and capture its id as the
    # conversation_id. The existing post-processing patches the stored content to
    # the cleaned version afterwards (see _patch_conversation_content).
    await set_tenant_context(session, str(tenant_id))
    assistant_id = await _save_customer_message(
        session, tenant_id, lead_id, session_id, canal,
        role="assistant", content=response_text, tokens=tokens_used,
        modelo=model_used, status="SENT",
    )
    await session.commit()

    # Build the response envelope for the caller. confianza is fixed at 0.95 for
    # the orchestrated route (there is no confidence classifier on this path).
    ai_response: dict = {
        "response": response_text,
        "conversation_id": str(assistant_id),
        "session_id": str(session_id) if session_id else None,
        "tokens_used": tokens_used,
        "confianza": 0.95,
        "sub_agente_usado": "ORCHESTRATED",
        "sources": [],
    }

    # Enrich order with mesa context before creating comanda
    order_data = extract_order_json(response_text)
    if order_data and mesa_context:
        _enrich_order_with_mesa(order_data, mesa_context)

    comanda_created = False
    if order_data and lead_id:
        logger.info(
            "Order JSON detected for tenant %s, lead %s: %d items",
            tenant_id, lead_id, len(order_data.get("items", [])),
        )
        comanda_created = await _create_comanda_from_order(
            tenant_id, lead_id, order_data, settings=settings,
        )
    elif not order_data:
        comanda_created = False
    else:
        logger.warning("Order JSON detected for tenant %s but lead_id is None", tenant_id)

    reserva_created = await _try_create_reservacion(response_text, tenant_id, lead_id, settings)

    clean_response = _strip_json_block(response_text)
    clean_response, media_attachments = await _resolve_media_markers(
        clean_response, config, tenant_id, settings=settings,
    )
    await _auto_attach_menu_pdf(message, config, media_attachments, tenant_id, settings)

    ai_response["response"] = clean_response
    conversation_id = ai_response.get("conversation_id")

    result = {**ai_response, "comanda_created": comanda_created, "reserva_created": reserva_created}
    _attach_first_media(result, media_attachments)

    # Debug log: confirm media + caption flow
    if result.get("media_url"):
        logger.info(
            "Media result: type=%s file=%s has_caption=%s caption_preview=%s",
            result.get("media_type"),
            result.get("media_file_name"),
            bool(result.get("media_caption")),
            (result.get("media_caption") or "")[:80],
        )

    # Defer the conversation-content patch: the reply is already built, so run it
    # fire-and-forget after we return (mirrors the notification pattern above).
    # _patch_conversation_content opens its own fresh session, so it does not
    # depend on the request `session` (which is closed once we return).
    if response_text != clean_response and conversation_id:
        import asyncio
        _patch_task = asyncio.create_task(
            _patch_conversation_content(
                None, tenant_id, conversation_id, clean_response, settings=settings,
            )
        )
        _patch_task.add_done_callback(
            lambda t: t.exception() if not t.cancelled() and t.exception() else None
        )

    return result


async def _patch_conversation_content(
    session: AsyncSession,
    tenant_id: UUID,
    conversation_id,
    clean_content: str,
    settings=None,
) -> None:
    """Update the stored AI conversation message to remove markers/artifacts.

    Uses a fresh DB connection to avoid disrupting the caller's transaction.
    """
    try:
        factory = _get_postprocess_factory(settings)
        async with factory() as fresh_session:
            await fresh_session.execute(
                sql_text(
                    "UPDATE ai_conversations SET content = :content "
                    "WHERE id = :cid AND tenant_id = :tid"
                ),
                {
                    "cid": str(conversation_id),
                    "tid": str(tenant_id),
                    "content": clean_content,
                },
            )
            await fresh_session.commit()
        logger.debug("Patched conversation %s content (cleaned markers)", conversation_id)
    except Exception:
        logger.warning("Failed to patch conversation %s content", conversation_id, exc_info=True)
