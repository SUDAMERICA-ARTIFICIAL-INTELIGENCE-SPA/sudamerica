"""Web scraper service — render SPAs and extract menu data via Browserless.io."""

import json
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

BROWSERLESS_BASE = "https://chrome.browserless.io"

# Security: block private IPs / non-HTTP URLs
_PRIVATE_PATTERNS = re.compile(
    r"^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.|127\.|0\.|localhost|::1)"
)


@dataclass
class ScrapedPage:
    """Result from rendering a web page."""
    screenshots: list[bytes] = field(default_factory=list)
    image_map: dict[str, str] = field(default_factory=dict)
    html_content: str = ""
    page_title: str = ""
    category_names: list[str] = field(default_factory=list)


def validate_url(url: str) -> str:
    """Validate and normalize URL. Raises ValueError for unsafe URLs."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Solo se aceptan URLs HTTP/HTTPS")
    if not parsed.netloc:
        raise ValueError("URL inválida — falta el dominio")
    if _PRIVATE_PATTERNS.match(parsed.hostname or ""):
        raise ValueError("No se puede acceder a direcciones privadas/internas")
    # Force HTTPS
    if parsed.scheme == "http":
        url = "https" + url[4:]
    return url


async def render_and_extract(
    url: str,
    api_key: str,
    timeout: int = 60,
) -> ScrapedPage:
    """Render a URL via Browserless.io and extract menu data.

    1. Takes a full-page screenshot
    2. Extracts all image URLs from rendered DOM
    3. Extracts category/tab names from DOM

    Returns ScrapedPage with screenshots and image_map.
    """
    url = validate_url(url)
    result = ScrapedPage()

    # Browserless /content endpoint — returns rendered HTML
    content_payload = {
        "url": url,
        "waitForSelector": {"selector": "body", "timeout": 10000},
        "gotoOptions": {"waitUntil": "networkidle2", "timeout": timeout * 1000},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=timeout + 10) as client:
        # Step 1: Get rendered HTML
        try:
            resp = await client.post(
                f"{BROWSERLESS_BASE}/content",
                json=content_payload,
                headers=headers,
            )
            resp.raise_for_status()
            result.html_content = resp.text
        except httpx.HTTPError as exc:
            logger.error("Browserless /content failed: %s", exc)
            raise RuntimeError(f"No se pudo renderizar la página: {exc}") from exc

        # Step 2: Take full-page screenshot
        screenshot_payload = {
            "url": url,
            "gotoOptions": {"waitUntil": "networkidle2", "timeout": timeout * 1000},
            "options": {"fullPage": True, "type": "png"},
        }
        try:
            resp = await client.post(
                f"{BROWSERLESS_BASE}/screenshot",
                json=screenshot_payload,
                headers=headers,
            )
            resp.raise_for_status()
            result.screenshots.append(resp.content)
        except httpx.HTTPError as exc:
            logger.warning("Browserless /screenshot failed: %s", exc)

    # Step 3: Extract image URLs from HTML
    result.image_map = _extract_image_urls(result.html_content, url)

    # Step 4: Extract category names from common patterns
    result.category_names = _extract_category_names(result.html_content)

    return result


_SKIP_PATTERNS = ("logo", "icon", "pixel", "tracking", "favicon", ".svg")


def _resolve_img_src(src: str, base_origin: str) -> str | None:
    """Resolve a potentially relative image src to an absolute URL."""
    if any(skip in src.lower() for skip in _SKIP_PATTERNS):
        return None
    if src.startswith("//"):
        return f"https:{src}"
    if src.startswith("/"):
        return f"{base_origin}{src}"
    if src.startswith("http"):
        return src
    return None


def _extract_image_urls(html: str, base_url: str) -> dict[str, str]:
    """Extract {alt_text: src_url} from <img> tags in rendered HTML."""
    img_pattern = re.compile(
        r'<img[^>]*?\bsrc=["\']([^"\']+)["\'][^>]*?\balt=["\']([^"\']*)["\']'
        r'|<img[^>]*?\balt=["\']([^"\']*)["\'][^>]*?\bsrc=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    parsed_base = urlparse(base_url)
    base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
    img_map: dict[str, str] = {}

    for match in img_pattern.finditer(html):
        src = match.group(1) or match.group(4) or ""
        alt = (match.group(2) or match.group(3) or "").strip()
        if not src or not alt:
            continue
        resolved = _resolve_img_src(src, base_origin)
        if resolved:
            img_map[alt] = resolved

    logger.info("Extracted %d images from HTML", len(img_map))
    return img_map


def _extract_category_names(html: str) -> list[str]:
    """Extract potential category/tab names from common DOM patterns."""
    names: list[str] = []
    # Look for tab/button patterns
    tab_pattern = re.compile(
        r'(?:role=["\']tab["\']|class=["\'][^"\']*tab[^"\']*["\'])[^>]*>([^<]{2,50})<',
        re.IGNORECASE,
    )
    for match in tab_pattern.finditer(html):
        name = match.group(1).strip()
        if name and name not in names:
            names.append(name)
    return names


def fuzzy_match_image(product_name: str, image_map: dict[str, str]) -> str | None:
    """Find best matching image URL for a product name using fuzzy matching."""
    if not image_map:
        return None
    name_lower = product_name.lower().strip()

    # Exact match
    for alt, url in image_map.items():
        if alt.lower().strip() == name_lower:
            return url

    # Contains match
    for alt, url in image_map.items():
        alt_lower = alt.lower().strip()
        if name_lower in alt_lower or alt_lower in name_lower:
            return url

    # Word overlap match (at least 2 words in common)
    name_words = set(name_lower.split())
    best_url = None
    best_overlap = 0
    for alt, url in image_map.items():
        alt_words = set(alt.lower().split())
        overlap = len(name_words & alt_words)
        if overlap > best_overlap and overlap >= 2:
            best_overlap = overlap
            best_url = url

    return best_url
