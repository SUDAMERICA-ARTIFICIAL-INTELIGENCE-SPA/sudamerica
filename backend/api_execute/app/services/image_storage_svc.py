"""Image storage service — upload product images to Google Cloud Storage."""

import io
import logging
import uuid as _uuid
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)

GCS_BUCKET = "sudamerica-menu-images"
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}

# Optional GCS import — falls back to URL-only mode if not available
try:
    from google.cloud import storage as gcs_storage
    _HAS_GCS = True
except ImportError:
    _HAS_GCS = False


def _to_webp(image_bytes: bytes) -> bytes:
    """Convert image to WebP format. Falls back to original if Pillow not available."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        # Limit to 1600x1600 max
        img.thumbnail((1600, 1600), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=82)
        return buf.getvalue()
    except ImportError:
        logger.warning("Pillow not installed — skipping WebP conversion")
        return image_bytes
    except Exception as exc:
        logger.warning("WebP conversion failed: %s", exc)
        return image_bytes


def _make_thumb(image_bytes: bytes, size: int = 400) -> bytes:
    """Generate thumbnail. Falls back to original if Pillow not available."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        img.thumbnail((size, size), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=75)
        return buf.getvalue()
    except (ImportError, Exception):
        return image_bytes


async def upload_product_image(
    tenant_id: UUID,
    producto_id: UUID,
    file_content: bytes,
    content_type: str,
    gcs_bucket_name: str = GCS_BUCKET,
) -> str:
    """Upload product image to GCS, return public URL.

    1. Validate type + size
    2. Convert to WebP
    3. Generate thumbnail
    4. Upload both to GCS
    5. Return URL of original
    """
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError(f"Tipo de imagen no soportado: {content_type}. Usa PNG, JPG o WebP.")

    if len(file_content) > MAX_IMAGE_SIZE:
        raise ValueError(f"Imagen muy grande ({len(file_content) // 1024}KB). Máximo {MAX_IMAGE_SIZE // (1024*1024)}MB.")

    if not _HAS_GCS:
        raise RuntimeError("google-cloud-storage no está instalado. Configura las dependencias de GCS.")

    webp_data = _to_webp(file_content)
    thumb_data = _make_thumb(file_content)

    prefix = f"{tenant_id}/productos/{producto_id}"
    original_path = f"{prefix}/original.webp"
    thumb_path = f"{prefix}/thumb_400.webp"

    client = gcs_storage.Client()
    bucket = client.bucket(gcs_bucket_name)

    # Upload original
    blob_orig = bucket.blob(original_path)
    blob_orig.upload_from_string(webp_data, content_type="image/webp")

    # Upload thumbnail
    blob_thumb = bucket.blob(thumb_path)
    blob_thumb.upload_from_string(thumb_data, content_type="image/webp")

    public_url = f"https://storage.googleapis.com/{gcs_bucket_name}/{original_path}"
    logger.info("Uploaded product image: %s (%d bytes)", original_path, len(webp_data))
    return public_url


async def delete_product_image(
    tenant_id: UUID,
    producto_id: UUID,
    gcs_bucket_name: str = GCS_BUCKET,
) -> None:
    """Delete product image (original + thumbnail) from GCS."""
    if not _HAS_GCS:
        return

    prefix = f"{tenant_id}/productos/{producto_id}"
    client = gcs_storage.Client()
    bucket = client.bucket(gcs_bucket_name)

    for suffix in ("original.webp", "thumb_400.webp"):
        blob = bucket.blob(f"{prefix}/{suffix}")
        if blob.exists():
            blob.delete()

    logger.info("Deleted product image: %s", prefix)


async def download_image(url: str, timeout: float = 15.0) -> tuple[bytes, str]:
    """Download image from external URL. Returns (content, content_type)."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    ct = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
    return resp.content, ct


async def batch_download_and_upload(
    items: list[dict],
    tenant_id: UUID,
    gcs_bucket_name: str = GCS_BUCKET,
    max_concurrent: int = 10,
) -> int:
    """Download images from URLs and upload to GCS for each item.

    Each item dict should have:
      - 'imagen_url_origen': URL to download from
      - 'producto_id': UUID of the product (set after _bulk_create)

    Returns number of images successfully uploaded.
    """
    import asyncio

    uploaded = 0
    sem = asyncio.Semaphore(max_concurrent)

    async def _process_one(item: dict) -> bool:
        url = item.get("imagen_url_origen")
        pid = item.get("producto_id")
        if not url or not pid:
            return False
        async with sem:
            try:
                content, ct = await download_image(url)
                if ct not in ALLOWED_IMAGE_TYPES:
                    ct = "image/jpeg"  # assume JPEG for unknown types
                public_url = await upload_product_image(
                    tenant_id, pid, content, ct, gcs_bucket_name
                )
                item["imagen_url"] = public_url
                return True
            except Exception as exc:
                logger.warning("Failed to download/upload image %s: %s", url, exc)
                return False

    results = await asyncio.gather(
        *[_process_one(item) for item in items],
        return_exceptions=True,
    )
    uploaded = sum(1 for r in results if r is True)
    return uploaded
