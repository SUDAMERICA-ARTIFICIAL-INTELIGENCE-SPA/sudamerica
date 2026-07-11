"""All Pydantic schemas for callback_manual."""

from app.schemas.revision import (
    RevisionAccionRequest,
    RevisionCreate,
    RevisionResponse,
    RevisionStats,
)
from app.schemas.transcription import TranscribeRequest, TranscribeResponse

__all__ = [
    "RevisionCreate",
    "RevisionResponse",
    "RevisionAccionRequest",
    "RevisionStats",
    "TranscribeRequest",
    "TranscribeResponse",
]
