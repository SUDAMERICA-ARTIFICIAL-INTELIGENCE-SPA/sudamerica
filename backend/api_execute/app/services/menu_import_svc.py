"""Menu import service — extract menu items from CSV, PDF, or images via AI."""

import base64
import csv
import io
import json
import logging
import re
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.services import web_scraper_svc
from app.services.image_storage_svc import batch_download_and_upload, download_image, upload_product_image
from app.services.rubro_prompt import extract_prompt_generico

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ApiExecuteSettings
from app.models.categoria import Categoria
from app.models.menu_import import MenuImport
from app.models.producto import Producto
from app.services.tenant_rubro import load_tenant_rubro as _load_tenant_rubro
from shared.database.session import set_tenant_context
from shared.rubros import RUBRO_DEFAULT
from shared.utils.storage import build_media_path, generate_signed_url, upload_bytes

logger = logging.getLogger(__name__)

SUPPORTED_CSV_EXTENSIONS = (".csv",)
SUPPORTED_AI_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".webp")

_EXTRACT_PROMPT = """Eres un sistema experto de extraccion de menus de restaurantes.
Analiza el archivo adjunto y extrae TODOS los items del menu, organizados correctamente.

Responde SOLO con JSON valido, sin texto adicional:
{
  "items": [
    {
      "nombre": "Nombre del plato (incluye tamaño/variante si aplica)",
      "descripcion": "Ingredientes o descripcion breve, o null",
      "precio": 5990,
      "categoria": "Seccion exacta del menu donde aparece"
    }
  ]
}

REGLAS CRITICAS DE ORGANIZACION:
- **categoria** debe ser la seccion/titulo/encabezado REAL del menu tal como aparece en el documento
  Ejemplos: "Pizzas Especiales", "Pizzas Clasicas", "Entradas", "Bebidas", "Postres", "Combos", "Extras"
- Si el menu tiene sub-secciones visibles, usalas como categoria (no inventes nombres genericos)
- Si un plato aparece con multiples tamaños/precios (ej: Chica $85, Mediana $130, Grande $180),
  crea UN item por cada tamaño con el formato: "NOMBRE - Tamaño" (ej: "Hawaiana - Chica")
- Si no hay seccion clara visible, agrupa por tipo logico: "Platos Principales", "Bebidas", "Postres", etc.
- NUNCA uses "General" si puedes inferir una categoria razonable del contexto

REGLAS DE DATOS:
- Precio SIEMPRE en numero entero (sin puntos ni comas de miles, sin simbolo $)
- Si el precio tiene decimales, redondea al entero mas cercano
- Si no puedes determinar el precio, pon 0
- descripcion: incluye ingredientes si estan visibles, o null si no hay descripcion
- Extrae TODOS los items, no solo algunos
- No inventes items que no estan en el documento
- Mantén el orden original en que aparecen en el menu"""


def build_extract_prompt(rubro_key: str) -> str:
    """System prompt de extracción según rubro.

    Restaurante conserva el prompt gastronómico original (byte-idéntico); otros
    rubros usan la versión generalizada basada en el vocabulario del rubro.
    """
    if rubro_key == RUBRO_DEFAULT:
        return _EXTRACT_PROMPT
    return extract_prompt_generico(rubro_key)


_NAME_KEYS = ("nombre", "name", "plato")
_PRICE_KEYS = ("precio", "price", "valor")
_DESC_KEYS = ("descripcion", "description")
_CAT_KEYS = ("categoria", "category", "seccion")


def _first_value(row: dict, keys: tuple[str, ...], default: str = "") -> str:
    """Return the first non-empty value from row for the given keys."""
    for k in keys:
        val = row.get(k)
        if val:
            return str(val).strip()
    return default


def _parse_precio(raw: str) -> int:
    """Clean and parse a price string into an integer."""
    cleaned = re.sub(r"[^\d.,]", "", raw).replace(",", ".")
    try:
        return int(Decimal(cleaned))
    except (InvalidOperation, ValueError):
        return 0


def _parse_csv_row(row: dict) -> dict | None:
    """Parse a single CSV row into a menu item dict, or None if invalid.

    ``precio`` is returned as ``float`` rather than ``Decimal`` because the
    item dict is stored in the ``menu_imports.preview_data`` JSONB column,
    and PostgreSQL's JSON serializer does not handle ``Decimal``.
    ``_build_producto`` re-parses via ``_parse_precio``, so downstream
    precision is preserved.
    """
    nombre = _first_value(row, _NAME_KEYS)
    if not nombre:
        return None
    return {
        "nombre": nombre,
        "descripcion": _first_value(row, _DESC_KEYS) or None,
        "precio": float(_parse_precio(_first_value(row, _PRICE_KEYS, "0"))),
        "categoria": _first_value(row, _CAT_KEYS, "General"),
    }


async def import_from_csv(
    file_content: bytes,
    tenant_id: UUID,
    db: AsyncSession,
) -> dict:
    """Parse CSV and create categorias + productos."""
    text = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    items = [item for row in reader if (item := _parse_csv_row(row)) is not None]

    if not items:
        return {"created": 0, "categories_created": 0, "errors": ["CSV vacío o sin columna 'nombre'"]}

    return await _bulk_create(items, tenant_id, db)


_MIME_MAP = {
    "application/pdf": "application/pdf",
    "image/png": "image/png",
    "image/webp": "image/webp",
}


def _build_ai_extraction_payload(
    file_content: bytes, filename: str, content_type: str, model: str,
    rubro_key: str = RUBRO_DEFAULT,
) -> tuple[list[dict], dict]:
    """Build the messages and payload for AI menu extraction."""
    base64_data = base64.b64encode(file_content).decode("utf-8")
    mime_type = _MIME_MAP.get(content_type, "image/jpeg")
    messages = [
        {"role": "system", "content": build_extract_prompt(rubro_key)},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}},
                {"type": "text", "text": f"Extrae todos los items del menu de este archivo: {filename}"},
            ],
        },
    ]
    return messages, {"model": model, "messages": messages, "temperature": 0.1, "max_tokens": 8192}


async def _call_ai_extraction(
    base_url: str, api_key: str, payload: dict,
) -> str | None:
    """Call the AI extraction endpoint. Returns response text or None on failure."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{base_url.rstrip('/')}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("AI menu extraction failed: %s", exc)
        return None
    return resp.json()["choices"][0]["message"]["content"]


async def import_from_ai(
    file_content: bytes,
    filename: str,
    content_type: str,
    tenant_id: UUID,
    db: AsyncSession,
    settings: ApiExecuteSettings,
) -> dict:
    """Use AI (Gemini Vision) to extract menu items from PDF/image."""
    api_key = settings.GEMINI_API_KEY or settings.OPENAI_API_KEY
    empty = {"created": 0, "categories_created": 0, "errors": []}
    if not api_key:
        return {**empty, "errors": ["No AI API key configured"]}

    rubro_key = await _load_tenant_rubro(db, tenant_id)
    _msgs, payload = _build_ai_extraction_payload(
        file_content, filename, content_type, settings.GEMINI_MODEL, rubro_key,
    )
    text = await _call_ai_extraction(settings.GEMINI_BASE_URL, api_key, payload)
    if text is None:
        return {**empty, "errors": ["AI extraction failed"]}

    items = _parse_ai_response(text)
    if not items:
        return {**empty, "errors": ["AI no pudo extraer items del archivo"], "raw_response": text[:500]}
    return await _bulk_create(items, tenant_id, db)


async def _render_page(url: str, settings) -> "web_scraper_svc.PageData | dict":
    """Render a URL and return PageData, or an error dict."""
    _empty = {"created": 0, "categories_created": 0, "images_uploaded": 0}
    try:
        page = await web_scraper_svc.render_and_extract(
            url=url, api_key=settings.BROWSERLESS_API_KEY, timeout=settings.BROWSERLESS_TIMEOUT,
        )
    except (ValueError, RuntimeError) as exc:
        return {**_empty, "errors": [str(exc)]}
    if not page.screenshots:
        return {**_empty, "errors": ["No se pudo capturar screenshot de la página"]}
    return page


async def _extract_items_from_screenshot(
    screenshot: bytes, url: str, api_key: str, settings,
    rubro_key: str = RUBRO_DEFAULT,
) -> list[dict] | dict:
    """Extract menu items from a screenshot via AI. Returns items or error dict."""
    _empty = {"created": 0, "categories_created": 0, "images_uploaded": 0}
    base64_data = base64.b64encode(screenshot).decode("utf-8")
    messages = [
        {"role": "system", "content": build_extract_prompt(rubro_key)},
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_data}"}},
            {"type": "text", "text": f"Extrae todos los items del menu visible en este screenshot del sitio: {url}"},
        ]},
    ]
    payload = {"model": settings.GEMINI_MODEL, "messages": messages, "temperature": 0.1, "max_tokens": 8192}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    ai_url = f"{settings.GEMINI_BASE_URL.rstrip('/')}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(ai_url, json=payload, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("AI extraction from URL screenshot failed: %s", exc)
        return {**_empty, "errors": [f"AI extraction failed: {exc}"]}
    text = resp.json()["choices"][0]["message"]["content"]
    items = _parse_ai_response(text)
    if not items:
        return {**_empty, "errors": ["AI no pudo extraer items de la página"], "raw_response": text[:500]}
    return items


def _match_images_to_items(items: list[dict], image_map: dict) -> None:
    """Match product images from DOM to extracted items in-place."""
    for item in items:
        matched = web_scraper_svc.fuzzy_match_image(item.get("nombre", ""), image_map)
        if matched:
            item["imagen_url_origen"] = matched


async def _upload_matched_images(items, tenant_id, settings, result) -> int:
    """Upload matched images to GCS. Returns count uploaded."""
    if not settings.GCS_BUCKET_NAME or not any(i.get("imagen_url_origen") for i in items):
        return 0
    try:
        return await batch_download_and_upload(items, tenant_id, settings.GCS_BUCKET_NAME)
    except Exception as exc:
        logger.warning("Image batch upload failed: %s", exc)
        result["errors"].append(f"Algunas imágenes no se pudieron subir: {exc}")
        return 0


async def import_from_url(
    url: str,
    tenant_id: UUID,
    db: AsyncSession,
    settings: "ApiExecuteSettings",
) -> dict:
    """Import menu from a website URL via web scraping + AI extraction.

    1. Render page via Browserless.io
    2. Take screenshot → send to Gemini Vision for extraction
    3. Match product images from DOM
    4. Download images → upload to GCS
    5. Bulk-create categorias + productos
    """
    _empty = {"created": 0, "categories_created": 0, "images_uploaded": 0}

    if not settings.BROWSERLESS_API_KEY:
        return {**_empty, "errors": ["BROWSERLESS_API_KEY no configurada"]}

    page = await _render_page(url, settings)
    if isinstance(page, dict):
        return page  # error dict

    api_key = settings.GEMINI_API_KEY or settings.OPENAI_API_KEY
    if not api_key:
        return {**_empty, "errors": ["No AI API key configured"]}

    rubro_key = await _load_tenant_rubro(db, tenant_id)
    items = await _extract_items_from_screenshot(page.screenshots[0], url, api_key, settings, rubro_key)
    if isinstance(items, dict):
        return items  # error dict

    _match_images_to_items(items, page.image_map)
    result = await _bulk_create(items, tenant_id, db)
    result["images_uploaded"] = await _upload_matched_images(items, tenant_id, settings, result)
    result["source_url"] = url
    return result


def _parse_ai_response(text: str) -> list[dict]:
    """Parse JSON from AI response, handling markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
    if not cleaned.startswith("{"):
        brace_start = cleaned.find("{")
        brace_end = cleaned.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            cleaned = cleaned[brace_start : brace_end + 1]
    try:
        result = json.loads(cleaned)
        return result.get("items", [])
    except json.JSONDecodeError:
        logger.error("Failed to parse AI menu extraction response: %s", text[:200])
        return []


def _parse_precio(raw: object) -> Decimal:
    """Parse a price value, returning Decimal(0) on failure."""
    try:
        return Decimal(str(raw)) if raw else Decimal("0")
    except (InvalidOperation, ValueError):
        return Decimal("0")


async def _load_category_map(db: AsyncSession, tenant_id: UUID) -> dict[str, UUID]:
    """Load existing active categories as a lowercase name -> id map."""
    existing_cats = await db.execute(
        select(Categoria).where(
            Categoria.tenant_id == tenant_id,
            Categoria.activo.is_(True),
        )
    )
    return {c.nombre.lower(): c.id for c in existing_cats.scalars().all()}


async def _ensure_category(
    db: AsyncSession, tenant_id: UUID, cat_name: str, cat_map: dict[str, UUID],
) -> UUID:
    """Return category ID, creating the category if it doesn't exist."""
    cat_key = cat_name.lower()
    if cat_key not in cat_map:
        new_cat = Categoria(tenant_id=tenant_id, nombre=cat_name)
        db.add(new_cat)
        await db.flush()
        cat_map[cat_key] = new_cat.id
    return cat_map[cat_key]


def _build_producto(
    tenant_id: UUID, categoria_id: UUID, item: dict, nombre: str,
) -> Producto:
    """Build a Producto instance from an extracted menu item."""
    return Producto(
        tenant_id=tenant_id,
        categoria_id=categoria_id,
        nombre=nombre,
        descripcion=item.get("descripcion"),
        precio=_parse_precio(item.get("precio", 0)),
        imagen_url=item.get("imagen_url"),
        stock=0,
    )


async def _bulk_create(
    items: list[dict],
    tenant_id: UUID,
    db: AsyncSession,
) -> dict:
    """Create categorias and productos from extracted items. Tenant-scoped."""
    cat_map = await _load_category_map(db, tenant_id)
    initial_cat_count = len(cat_map)
    productos_batch: list[Producto] = []

    for item in items:
        nombre = (item.get("nombre") or "").strip()
        if not nombre:
            continue
        cat_name = (item.get("categoria") or "General").strip()
        categoria_id = await _ensure_category(db, tenant_id, cat_name, cat_map)
        productos_batch.append(_build_producto(tenant_id, categoria_id, item, nombre))

    for p in productos_batch:
        db.add(p)
    if productos_batch:
        await db.flush()
    await db.commit()

    created = len(productos_batch)
    categories_created = len(cat_map) - initial_cat_count
    logger.info("Menu import: tenant=%s created=%d categories=%d", tenant_id, created, categories_created)
    return {"created": created, "categories_created": categories_created, "errors": []}


# ── Preview / Confirm workflow ──────────────────────────────────────


_SOURCE_TYPE_MAP: dict[str, str] = {
    ".pdf": "PDF",
    ".csv": "CSV",
    ".png": "IMAGE",
    ".jpg": "IMAGE",
    ".jpeg": "IMAGE",
    ".webp": "IMAGE",
}


async def _next_version(db: AsyncSession, tenant_id: UUID) -> int:
    """Compute next menu version number for a tenant."""
    result = await db.execute(
        select(func.coalesce(func.max(MenuImport.version), 0)).where(
            MenuImport.tenant_id == tenant_id,
        )
    )
    return (result.scalar() or 0) + 1


def _detect_source_type(filename: str) -> str:
    """Map file extension to source_type enum value."""
    lower = filename.lower()
    for ext, stype in _SOURCE_TYPE_MAP.items():
        if lower.endswith(ext):
            return stype
    return "IMAGE"


async def _persist_original_file(
    file_content: bytes,
    filename: str,
    content_type: str,
    tenant_id: UUID,
    bucket_name: str,
) -> tuple[str, str]:
    """Upload the original file to GCS. Returns (blob_path, signed_url)."""
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    blob_path = build_media_path(str(tenant_id), "menu-original", ext)
    upload_bytes(bucket_name, file_content, blob_path, content_type)
    signed_url = generate_signed_url(bucket_name, blob_path)
    return blob_path, signed_url


async def extract_preview(
    file_content: bytes,
    filename: str,
    content_type: str,
    tenant_id: UUID,
    db: AsyncSession,
    settings: ApiExecuteSettings,
) -> dict:
    """Phase 1: Upload original file to GCS, extract items via AI, return preview.

    Does NOT create productos/categorias — those are created on confirm.
    """
    api_key = settings.GEMINI_API_KEY or settings.OPENAI_API_KEY
    if not api_key:
        return {"error": "No AI API key configured"}

    # 1. Persist original file in GCS
    blob_path, signed_url = await _persist_original_file(
        file_content, filename, content_type, tenant_id, settings.GCS_BUCKET_NAME,
    )

    # 2. AI extraction (reuse existing logic)
    rubro_key = await _load_tenant_rubro(db, tenant_id)
    _msgs, payload = _build_ai_extraction_payload(
        file_content, filename, content_type, settings.GEMINI_MODEL, rubro_key,
    )
    text = await _call_ai_extraction(settings.GEMINI_BASE_URL, api_key, payload)
    if text is None:
        return {"error": "AI extraction failed"}

    items = _parse_ai_response(text)
    if not items:
        return {"error": "AI no pudo extraer items del archivo", "raw_response": text[:500]}

    # 3. Compute next version
    version = await _next_version(db, tenant_id)

    # 4. Create menu_imports row with status=PENDING
    source_type = _detect_source_type(filename)
    record = MenuImport(
        tenant_id=tenant_id,
        version=version,
        source_type=source_type,
        filename=filename,
        original_pdf_path=blob_path,
        original_pdf_url=signed_url,
        file_size_bytes=len(file_content),
        content_type=content_type,
        items_extracted=len(items),
        preview_data={"items": items},
        status="PENDING",
    )
    db.add(record)
    await db.flush()
    await db.commit()

    return {
        "import_id": str(record.id),
        "items": items,
        "source_type": source_type,
        "filename": filename,
    }


async def extract_preview_csv(
    file_content: bytes,
    tenant_id: UUID,
    db: AsyncSession,
    settings: ApiExecuteSettings,
) -> dict:
    """Phase 1 for CSV: parse items and return preview without creating records."""
    text = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    items = [item for row in reader if (item := _parse_csv_row(row)) is not None]
    if not items:
        return {"error": "CSV vacío o sin columna 'nombre'"}

    version = await _next_version(db, tenant_id)
    record = MenuImport(
        tenant_id=tenant_id,
        version=version,
        source_type="CSV",
        filename="upload.csv",
        file_size_bytes=len(file_content),
        content_type="text/csv",
        items_extracted=len(items),
        preview_data={"items": items},
        status="PENDING",
    )
    db.add(record)
    await db.flush()
    await db.commit()

    return {
        "import_id": str(record.id),
        "items": items,
        "source_type": "CSV",
        "filename": "upload.csv",
    }


async def confirm_import(
    import_id: UUID,
    items: list[dict],
    tenant_id: UUID,
    db: AsyncSession,
    set_as_official: bool = False,
    settings: ApiExecuteSettings | None = None,
) -> dict:
    """Phase 2: Admin confirmed reviewed items — bulk-create productos/categorias."""
    # 1. Validate the menu_imports row
    result = await db.execute(
        select(MenuImport).where(
            MenuImport.id == import_id,
            MenuImport.tenant_id == tenant_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        return {"error": "Import not found"}
    if record.status != "PENDING":
        return {"error": f"Import already {record.status.lower()}"}

    # 2. Bulk create (reuse existing logic)
    create_result = await _bulk_create(items, tenant_id, db)

    # 3. Update menu_imports record.
    # `_bulk_create` commits, which ends the transaction and clears
    # `SET LOCAL app.current_tenant_id`. Without reapplying it, RLS
    # filters out the `menu_imports` row on UPDATE and SQLAlchemy raises
    # StaleDataError("0 were matched").
    await set_tenant_context(db, str(tenant_id))
    record.status = "CONFIRMED"
    record.items_confirmed = create_result["created"]
    record.categories_created = create_result["categories_created"]
    record.set_as_official = set_as_official
    await db.flush()
    await db.commit()

    # 4. If set_as_official, update agente_config.menu_pdf_url via AI_dialer
    if set_as_official and record.original_pdf_url and settings:
        await _update_official_menu_pdf(tenant_id, record.original_pdf_url, settings)

    return {
        "created": create_result["created"],
        "categories_created": create_result["categories_created"],
        "errors": create_result["errors"],
        "import_id": str(record.id),
        "version": record.version,
    }


async def _update_official_menu_pdf(
    tenant_id: UUID,
    pdf_url: str,
    settings: ApiExecuteSettings,
) -> None:
    """Update agente_config.menu_pdf_url via internal HTTP call to AI_dialer."""
    from shared.middleware import build_service_auth_headers
    from shared.utils.http_client import internal_http

    headers = build_service_auth_headers(
        service_name="api_execute",
        audience="ai_dialer",
        tenant_id=tenant_id,
        secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        scopes=("config:write",),
        expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )
    headers["X-Tenant-ID"] = str(tenant_id)

    try:
        resp = await internal_http.patch(
            f"{settings.SERVICE_AI_DIALER_URL}/api/v1/ai/config",
            json={"menu_pdf_url": pdf_url},
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        logger.info("Updated official menu PDF for tenant %s", tenant_id)
    except (httpx.HTTPError, RuntimeError):
        logger.warning(
            "Failed to update official menu PDF for tenant %s", tenant_id, exc_info=True,
        )


async def get_import_history(
    tenant_id: UUID,
    db: AsyncSession,
) -> list[dict]:
    """Return list of past menu imports for a tenant, newest first."""
    result = await db.execute(
        select(MenuImport)
        .where(
            MenuImport.tenant_id == tenant_id,
            MenuImport.activo.is_(True),
        )
        .order_by(MenuImport.version.desc())
        .limit(50)
    )
    records = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "version": r.version,
            "source_type": r.source_type,
            "filename": r.filename,
            "items_extracted": r.items_extracted,
            "items_confirmed": r.items_confirmed,
            "categories_created": r.categories_created,
            "status": r.status,
            "set_as_official": r.set_as_official,
            "original_pdf_url": r.original_pdf_url,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]
