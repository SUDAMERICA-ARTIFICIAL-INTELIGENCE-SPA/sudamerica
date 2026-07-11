"""Auto-generate a professional menu PDF from the product catalog.

Smart grouping:
- Detects size variants (e.g., "Hawaiana - Chica", "Hawaiana - Grande")
  and groups them into a single entry with a price row per size.
- Products without size variants are listed normally.
- Groups everything by category.
"""

import logging
import re
from uuid import UUID

from fpdf import FPDF
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.utils.storage import build_media_path, generate_signed_url, upload_bytes

logger = logging.getLogger(__name__)

# Common size suffixes found in restaurant product names
_SIZE_PATTERN = re.compile(
    r"^(.+?)\s*[-–]\s*(chica|mediana|grande|familiar|magna|personal|xl|xxl|mini|junior|small|medium|large|extra.large)$",
    re.IGNORECASE,
)

# Canonical size order for the price table
_SIZE_ORDER = [
    "mini", "chica", "personal", "junior", "small",
    "mediana", "medium", "grande", "large", "xl",
    "familiar", "magna", "xxl", "extra large",
]


def _size_sort_key(size: str) -> int:
    low = size.lower().strip()
    try:
        return _SIZE_ORDER.index(low)
    except ValueError:
        return 999


def _safe(text: str | None) -> str:
    if not text:
        return ""
    return text.encode("latin-1", errors="replace").decode("latin-1")


# ── Data loading ──────────────────────────────────────────────────────

async def _load_menu_data(
    session: AsyncSession,
    tenant_id: UUID,
) -> tuple[str, list[dict]]:
    """Load restaurant name and products grouped by category with smart size grouping."""
    name_result = await session.execute(
        sql_text("SELECT nombre FROM tenants WHERE id = :tid"),
        {"tid": str(tenant_id)},
    )
    restaurant_name = name_result.scalar_one_or_none() or "Restaurante"

    cat_result = await session.execute(
        sql_text(
            "SELECT id, nombre FROM categorias "
            "WHERE tenant_id = :tid AND activo = true ORDER BY nombre"
        ),
        {"tid": str(tenant_id)},
    )
    categories = {str(r["id"]): r["nombre"] for r in cat_result.mappings().all()}

    prod_result = await session.execute(
        sql_text(
            "SELECT nombre, descripcion, precio, categoria_id, disponible "
            "FROM productos WHERE tenant_id = :tid AND activo = true AND disponible = true "
            "ORDER BY categoria_id, nombre"
        ),
        {"tid": str(tenant_id)},
    )
    products = [dict(r) for r in prod_result.mappings().all()]

    # Group by category
    cat_products: dict[str, list[dict]] = {}
    for p in products:
        cat_id = str(p.get("categoria_id") or "")
        cat_name = categories.get(cat_id, "Otros")
        cat_products.setdefault(cat_name, []).append(p)

    # Smart grouping: detect size variants within each category
    menu_sections = []
    for cat_name, prods in cat_products.items():
        grouped_items = _group_size_variants(prods)
        menu_sections.append({"category": cat_name, "items": grouped_items})

    return restaurant_name, menu_sections


def _split_by_size_pattern(products: list[dict]) -> tuple[dict[str, list[dict]], list[dict]]:
    """Partition products into size-variant groups and singles."""
    base_groups: dict[str, list[dict]] = {}
    singles: list[dict] = []
    for p in products:
        match = _SIZE_PATTERN.match(p["nombre"])
        if match:
            base_name = match.group(1).strip()
            size = match.group(2).strip()
            base_groups.setdefault(base_name, []).append({
                "size": size, "price": p["precio"], "desc": p.get("descripcion") or "",
            })
        else:
            singles.append(p)
    return base_groups, singles


def _build_grouped_items(base_groups: dict[str, list[dict]]) -> list[dict]:
    """Convert size-variant groups into grouped menu items."""
    result: list[dict] = []
    for base_name, variants in sorted(base_groups.items()):
        variants.sort(key=lambda v: _size_sort_key(v["size"]))
        desc = variants[0]["desc"] if variants else ""
        result.append({
            "type": "grouped",
            "name": base_name,
            "desc": desc,
            "sizes": [{"size": v["size"].capitalize(), "price": v["price"]} for v in variants],
        })
    return result


def _group_size_variants(products: list[dict]) -> list[dict]:
    """Group products by base name, detecting size variants.

    Returns a list of items where each item is either:
    - A single product (no size variants): {"type": "single", "name": ..., "price": ..., "desc": ...}
    - A grouped product (has sizes): {"type": "grouped", "name": ..., "desc": ..., "sizes": [{"size": ..., "price": ...}]}
    """
    base_groups, singles = _split_by_size_pattern(products)
    result = _build_grouped_items(base_groups)
    result.extend(
        {"type": "single", "name": p["nombre"], "price": p["precio"], "desc": p.get("descripcion") or ""}
        for p in singles
    )
    return result


# ── PDF generation ────────────────────────────────────────────────────

_ACCENT = (76, 110, 245)   # Indigo
_DARK = (33, 37, 41)       # Near-black
_GRAY = (120, 120, 120)
_LIGHT_BG = (245, 246, 250)
_WHITE = (255, 255, 255)


class MenuPDF(FPDF):
    def __init__(self, restaurant_name: str):
        super().__init__()
        self.restaurant_name = restaurant_name
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 15, 15)

    def header(self):
        # Restaurant name
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(*_DARK)
        self.cell(0, 14, _safe(self.restaurant_name), align="C", new_x="LMARGIN", new_y="NEXT")

        # Subtitle
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*_GRAY)
        self.cell(0, 6, "Nuestra Carta", align="C", new_x="LMARGIN", new_y="NEXT")

        # Accent line
        self.set_draw_color(*_ACCENT)
        self.set_line_width(0.8)
        y = self.get_y() + 3
        center = self.w / 2
        self.line(center - 30, y, center + 30, y)
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(180, 180, 180)
        self.cell(0, 8, f"Menu generado por Sudamérica AI  |  Pag {self.page_no()}/{{nb}}", align="C")


def _render_category_header(pdf: MenuPDF, category: str):
    """Render a category section header."""
    pdf.ln(3)
    pdf.set_fill_color(*_ACCENT)
    pdf.set_text_color(*_WHITE)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, f"   {_safe(category.upper())}", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*_DARK)
    pdf.ln(4)


def _render_grouped_item(pdf: MenuPDF, item: dict):
    """Render a product with size variants as a compact price row."""
    w = pdf.w - pdf.l_margin - pdf.r_margin

    # Product name
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*_DARK)
    pdf.cell(w, 6, _safe(item["name"]), new_x="LMARGIN", new_y="NEXT")

    # Description
    desc = _safe(item.get("desc", ""))
    if desc:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*_GRAY)
        pdf.multi_cell(w, 4, desc)

    # Size/price row as a mini table
    sizes = item["sizes"]
    col_w = min(w / len(sizes), 36)
    table_w = col_w * len(sizes)
    start_x = pdf.l_margin + (w - table_w) / 2

    # Size labels
    pdf.set_x(start_x)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*_GRAY)
    for s in sizes:
        pdf.cell(col_w, 4, _safe(s["size"]), align="C")
    pdf.ln()

    # Prices
    pdf.set_x(start_x)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*_ACCENT)
    for s in sizes:
        pdf.cell(col_w, 5, f"${s['price']:,.0f}", align="C")
    pdf.ln()
    pdf.set_text_color(*_DARK)
    pdf.ln(3)


def _render_single_item(pdf: MenuPDF, item: dict):
    """Render a single product (no size variants)."""
    w = pdf.w - pdf.l_margin - pdf.r_margin
    name = _safe(item["name"])
    price = item.get("price", 0)
    desc = _safe(item.get("desc", ""))

    # Name + price on same line
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*_DARK)
    name_w = pdf.get_string_width(name) + 2
    price_str = f"${price:,.0f}"

    pdf.cell(name_w, 5, name)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*_ACCENT)
    pdf.cell(w - name_w, 5, price_str, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*_DARK)

    if desc:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*_GRAY)
        pdf.multi_cell(w, 4, desc)
        pdf.set_text_color(*_DARK)

    pdf.ln(2)


def _render_section_items(pdf, items: list[dict]) -> None:
    """Render all items for a single menu section."""
    for item in items:
        if pdf.get_y() > pdf.h - 35:
            pdf.add_page()
        if item["type"] == "grouped":
            _render_grouped_item(pdf, item)
        else:
            _render_single_item(pdf, item)


def _generate_pdf_bytes(restaurant_name: str, menu_sections: list[dict]) -> bytes:
    pdf = MenuPDF(_safe(restaurant_name))
    pdf.alias_nb_pages()
    pdf.add_page()

    if not menu_sections:
        pdf.set_font("Helvetica", "I", 12)
        pdf.cell(0, 10, "Menu en construccion", align="C")
        return bytes(pdf.output())

    for section in menu_sections:
        if not section["items"]:
            continue
        _render_category_header(pdf, section["category"])
        _render_section_items(pdf, section["items"])

    return bytes(pdf.output())


# ── Public API ────────────────────────────────────────────────────────

async def generate_menu_pdf(
    session: AsyncSession,
    tenant_id: UUID,
    bucket_name: str,
) -> str | None:
    """Generate a menu PDF from the product catalog and upload to GCS.

    Returns the signed URL of the generated PDF, or None if no products exist.
    """
    restaurant_name, menu_sections = await _load_menu_data(session, tenant_id)

    total_products = sum(len(s["items"]) for s in menu_sections)
    if total_products == 0:
        logger.info("No products found for tenant %s, skipping PDF generation", tenant_id)
        return None

    pdf_bytes = _generate_pdf_bytes(restaurant_name, menu_sections)
    logger.info(
        "Generated menu PDF for %s: %d categories, %d items, %d bytes",
        restaurant_name, len(menu_sections), total_products, len(pdf_bytes),
    )

    blob_path = f"tenants/{tenant_id}/media/document/menu-auto.pdf"
    upload_bytes(bucket_name, pdf_bytes, blob_path, content_type="application/pdf")
    signed_url = generate_signed_url(bucket_name, blob_path, expiration_hours=168)
    return signed_url
