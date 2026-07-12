"""Admin copilot chat endpoint — receives orchestrated requests from api_execute."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from shared.middleware.auth import require_service

from app.schemas.chat import (
    GenerateRequest,
    GenerateResponse,
    SudamericaChatRequest,
    SudamericaChatResponse,
)
from app.services.agent_engine import generate_response, run_agent

router = APIRouter(tags=["agent"])


@router.post("/chat", response_model=SudamericaChatResponse)
async def agent_chat(
    body: SudamericaChatRequest,
    request: Request,
    current_service: dict = Depends(
        require_service("sudamerica:chat", callers=("api_execute",))
    ),
):
    """Process an admin copilot message through the tool-calling agent loop."""
    settings = request.app.state.settings
    http_client = getattr(request.app.state, "http_client", None)
    tenant_id = str(current_service["tenant_id"])

    try:
        result = await run_agent(
            system_prompt=body.system_prompt,
            message=body.message,
            history=body.history,
            tenant_id=tenant_id,
            settings=settings,
            http_client=http_client,
            file=body.file,
            capabilities=body.capacidades,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error en el copiloto administrativo: {exc}",
        ) from exc

    return result


@router.post("/generate", response_model=GenerateResponse)
async def agent_generate(
    body: GenerateRequest,
    request: Request,
    current_service: dict = Depends(
        require_service("generate:chat", callers=("api_execute",))
    ),
):
    """Pure text generation (NO tools) for the customer chat and onboarding.

    api_execute owns the prompt, history and persistence; this endpoint only
    generates text. The admin TOOL_DEFINITIONS are never exposed here — they
    stay isolated to the /chat endpoint.
    """
    settings = request.app.state.settings
    http_client = getattr(request.app.state, "http_client", None)

    try:
        result = await generate_response(
            system_prompt=body.system_prompt,
            message=body.message,
            history=body.history,
            settings=settings,
            http_client=http_client,
            file=body.file,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error en la generacion de texto: {exc}",
        ) from exc

    return result
