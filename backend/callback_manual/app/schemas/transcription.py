"""Pydantic schemas for audio transcription endpoints."""

from pydantic import AnyHttpUrl, BaseModel


class TranscribeRequest(BaseModel):
    """Request schema for audio transcription."""

    audio_url: AnyHttpUrl


class TranscribeResponse(BaseModel):
    """Response schema for audio transcription."""

    text: str
    duration_seconds: float
