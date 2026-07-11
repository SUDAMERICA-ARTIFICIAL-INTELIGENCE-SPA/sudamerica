"""Audio transcription endpoint using Whisper."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from shared.middleware import get_current_user

from app.schemas.transcription import TranscribeRequest, TranscribeResponse
from app.services import transcription_service

router = APIRouter(tags=["transcription"])


@router.post("/transcription", response_model=TranscribeResponse)
@router.post("/reviews/transcription", response_model=TranscribeResponse, include_in_schema=False)
async def transcribe(
    body: TranscribeRequest,
    request: Request,
    _current_user: dict = Depends(get_current_user),
) -> TranscribeResponse:
    """Transcribe an audio file via OpenAI Whisper API."""
    api_key = request.app.state.settings.OPENAI_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY not configured",
        )
    try:
        text, duration = await transcription_service.transcribe_audio(
            audio_url=str(body.audio_url),
            api_key=api_key,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return TranscribeResponse(text=text, duration_seconds=duration)
