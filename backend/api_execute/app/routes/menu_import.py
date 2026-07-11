"""Menu import route — upload CSV, PDF, or image to bulk-create menu items."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db

from app.routes.deps import AdminWriter, get_settings
from app.schemas.menu_import import (
    ImportUrlRequest,
    MenuImportConfirmRequest,
    MenuImportConfirmResponse,
    MenuImportHistoryItem,
    MenuImportPreviewResponse,
)
from app.services import menu_import_svc

router = APIRouter(prefix="/menu", tags=["menu-import"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = (
    *menu_import_svc.SUPPORTED_CSV_EXTENSIONS,
    *menu_import_svc.SUPPORTED_AI_EXTENSIONS,
)


@router.post("/import")
async def import_menu(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Import menu items from CSV, PDF, or image file."""
    settings = get_settings(request)
    tenant_id = current_user["tenant_id"]

    filename = (file.filename or "upload").lower()
    ext = ""
    for e in ALLOWED_EXTENSIONS:
        if filename.endswith(e):
            ext = e
            break

    if not ext:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado. Usa: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Archivo muy grande (máx 10 MB)")

    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    if ext in menu_import_svc.SUPPORTED_CSV_EXTENSIONS:
        return await menu_import_svc.import_from_csv(content, tenant_id, db)

    return await menu_import_svc.import_from_ai(
        file_content=content,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        tenant_id=tenant_id,
        db=db,
        settings=settings,
    )


@router.post("/import-url")
async def import_menu_from_url(
    body: ImportUrlRequest,
    request: Request,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Import menu items from a website URL (renders SPA, extracts via AI)."""
    settings = get_settings(request)
    tenant_id = current_user["tenant_id"]

    return await menu_import_svc.import_from_url(
        url=body.url,
        tenant_id=tenant_id,
        db=db,
        settings=settings,
    )


# ── Preview / Confirm workflow ──


@router.post("/import/preview", response_model=MenuImportPreviewResponse)
async def preview_menu_import(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Phase 1: Extract items from file, persist original, return preview for review."""
    settings = get_settings(request)
    tenant_id = current_user["tenant_id"]

    filename = (file.filename or "upload").lower()
    ext = ""
    for e in ALLOWED_EXTENSIONS:
        if filename.endswith(e):
            ext = e
            break

    if not ext:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado. Usa: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Archivo muy grande (máx 10 MB)")
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    if ext in menu_import_svc.SUPPORTED_CSV_EXTENSIONS:
        result = await menu_import_svc.extract_preview_csv(content, tenant_id, db, settings)
    else:
        result = await menu_import_svc.extract_preview(
            file_content=content,
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            tenant_id=tenant_id,
            db=db,
            settings=settings,
        )

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    return result


@router.post("/import/confirm", response_model=MenuImportConfirmResponse)
async def confirm_menu_import(
    body: MenuImportConfirmRequest,
    request: Request,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Phase 2: Admin reviewed items — confirm and bulk-create productos/categorias."""
    settings = get_settings(request)
    tenant_id = current_user["tenant_id"]

    items = [item.model_dump() for item in body.items]
    result = await menu_import_svc.confirm_import(
        import_id=UUID(body.import_id),
        items=items,
        tenant_id=tenant_id,
        db=db,
        set_as_official=body.set_as_official_pdf,
        settings=settings,
    )

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    return result


@router.get("/import/history", response_model=list[MenuImportHistoryItem])
async def get_import_history(
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """List past menu imports for this tenant (versioning)."""
    return await menu_import_svc.get_import_history(current_user["tenant_id"], db)
