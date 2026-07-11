"""Sudamérica AI endpoints — admin copilot for restaurant owners/managers."""

import base64
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.dependencies import get_db
from shared.middleware.auth import require_role
from shared.models.enums import UserRole

from app.routes.deps import AdminWriter
from app.services.sudamerica_orchestrator import orchestrate_sudamerica_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sudamerica", tags=["sudamerica"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {
    "image/png", "image/jpeg", "image/webp", "image/gif",
    "application/pdf",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


async def _validate_and_encode_file(file: UploadFile | None) -> dict | None:
    """Validate the uploaded file and return base64-encoded data, or None."""
    if not file or not file.filename:
        return None
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no soportado: {file.content_type}. "
                   f"Tipos validos: imagenes, PDF, CSV, Excel.",
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Archivo muy grande ({len(content) // 1024}KB). "
                   f"Maximo: {MAX_FILE_SIZE // 1024 // 1024}MB.",
        )
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "data_base64": base64.b64encode(content).decode("ascii"),
    }


@router.post("/chat")
async def sudamerica_chat(
    request: Request,
    message: str = Form(...),
    file: UploadFile | None = File(None),
    current_user: dict = Depends(require_role(UserRole.SUPERADMIN, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    """Send a message to Sudamérica AI — the admin copilot. Optionally attach a file."""
    file_data = await _validate_and_encode_file(file)
    try:
        return await orchestrate_sudamerica_chat(
            session=session,
            tenant_id=current_user["tenant_id"],
            usuario_id=current_user["user_id"],
            user_name=current_user.get("nombre", ""),
            message=message,
            settings=request.app.state.settings,
            file_data=file_data,
        )
    except Exception:
        logger.exception("Sudamérica AI chat failed for tenant %s", current_user["tenant_id"])
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error comunicando con el copiloto. Intenta de nuevo.",
        )


@router.get("/history")
async def sudamerica_history(
    page: int = 1,
    page_size: int = 50,
    current_user: dict = Depends(require_role(UserRole.SUPERADMIN, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    """Get Sudamérica AI conversation history for the current user."""
    tenant_id = current_user["tenant_id"]
    usuario_id = current_user["user_id"]
    offset = (page - 1) * page_size

    count_result = await session.execute(
        sql_text(
            "SELECT COUNT(*) FROM ai_conversations "
            "WHERE tenant_id = :tid AND usuario_id = :uid AND canal = 'SUDAMERICA'"
        ),
        {"tid": str(tenant_id), "uid": str(usuario_id)},
    )
    total = count_result.scalar_one()

    result = await session.execute(
        sql_text(
            "SELECT id, role, content, tokens_used, modelo, created_at "
            "FROM ai_conversations "
            "WHERE tenant_id = :tid AND usuario_id = :uid AND canal = 'SUDAMERICA' "
            "ORDER BY created_at DESC "
            "LIMIT :lim OFFSET :off"
        ),
        {
            "tid": str(tenant_id),
            "uid": str(usuario_id),
            "lim": page_size,
            "off": offset,
        },
    )
    rows = result.mappings().all()

    messages = [
        {
            "id": str(r["id"]),
            "role": r["role"],
            "content": r["content"],
            "tokens_used": r["tokens_used"],
            "modelo": r["modelo"],
            "created_at": str(r["created_at"]),
        }
        for r in reversed(rows)
    ]

    return {
        "data": messages,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
