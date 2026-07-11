"""Base Pydantic v2 schemas shared across services."""

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: dict

    @classmethod
    def build(
        cls,
        items: list,
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse":
        """Create a PaginatedResponse with computed total_pages."""
        total_pages = max(1, (total + page_size - 1) // page_size)
        return cls(
            data=items,
            meta={
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            },
        )


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str = "0.1.0"
