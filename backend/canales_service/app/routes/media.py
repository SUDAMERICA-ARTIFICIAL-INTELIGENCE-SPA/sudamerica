"""Media upload endpoint — allows frontend to upload files to GCS."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.whatsapp import MediaType, MediaUploadResponse
from app.services.media_service import upload_media_to_gcs
from shared.database.dependencies import get_db
from shared.middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["media"])
CurrentUser = Annotated[dict, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]

_MAX_FILE_SIZE_MB = 16  # WhatsApp limit for documents is 16MB, images 5MB
_ALLOWED_MIMETYPES: dict[str, MediaType] = {
    # Images
    "image/jpeg": "image",
    "image/png": "image",
    "image/gif": "image",
    "image/webp": "image",
    # Documents
    "application/pdf": "document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
    "application/msword": "document",
    "application/vnd.ms-excel": "document",
    "text/csv": "document",
    # Video
    "video/mp4": "video",
    "video/3gpp": "video",
    # Audio
    "audio/ogg": "audio",
    "audio/mpeg": "audio",
    "audio/mp4": "audio",
    "audio/wav": "audio",
}


def _validate_content_type(file: UploadFile) -> tuple[str, MediaType]:
    """Validate file content type. Returns (content_type, media_type) or raises."""
    content_type = (file.content_type or "").lower()
    media_type = _ALLOWED_MIMETYPES.get(content_type)
    if not media_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Tipo de archivo no soportado: {content_type}. "
                   f"Formatos permitidos: JPG, PNG, GIF, PDF, XLSX, DOCX, MP4, OGG, MP3",
        )
    return content_type, media_type


async def _read_and_validate_size(file: UploadFile) -> bytes:
    """Read file data and enforce size limit."""
    data = await file.read()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > _MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo excede el límite de {_MAX_FILE_SIZE_MB}MB ({size_mb:.1f}MB)",
        )
    return data


@router.post("/media/upload", response_model=MediaUploadResponse)
async def upload_media(
    request: Request,
    file: UploadFile = File(...),
    current_user: CurrentUser = None,
    db: DbSession = None,
) -> MediaUploadResponse:
    """Upload a media file to GCS for sending via WhatsApp."""
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No tenant context")

    content_type, media_type = _validate_content_type(file)
    data = await _read_and_validate_size(file)

    try:
        _, signed_url = await upload_media_to_gcs(
            data=data, tenant_id=UUID(str(tenant_id)),
            media_type=media_type, mimetype=content_type,
            settings=request.app.state.settings,
        )
    except Exception as exc:
        logger.exception("Failed to upload media to GCS")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al subir archivo al almacenamiento",
        ) from exc

    return MediaUploadResponse(
        success=True, media_url=signed_url, media_type=media_type,
        file_name=file.filename, mimetype=content_type,
    )
