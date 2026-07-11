"""Menu import Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


class ImportUrlRequest(BaseModel):
    url: str


# ── Preview / Confirm workflow ──


class MenuImportPreviewItem(BaseModel):
    nombre: str
    descripcion: str | None = None
    precio: int = 0
    categoria: str = "General"


class MenuImportPreviewResponse(BaseModel):
    import_id: str
    items: list[MenuImportPreviewItem]
    source_type: str
    filename: str | None = None


class MenuImportConfirmRequest(BaseModel):
    import_id: str
    items: list[MenuImportPreviewItem]
    set_as_official_pdf: bool = False


class MenuImportConfirmResponse(BaseModel):
    created: int
    categories_created: int
    errors: list[str]
    import_id: str
    version: int


# ── Import history ──


class MenuImportHistoryItem(BaseModel):
    id: str
    version: int
    source_type: str
    filename: str | None = None
    items_extracted: int
    items_confirmed: int
    categories_created: int
    status: str
    set_as_official: bool
    original_pdf_url: str | None = None
    created_at: datetime
