"""MenuImport model — tracks menu import sessions with versioning."""

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import TenantBase


class MenuImport(TenantBase):
    __tablename__ = "menu_imports"
    __table_args__ = {"extend_existing": True}

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    items_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_confirmed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    categories_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    preview_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    set_as_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
