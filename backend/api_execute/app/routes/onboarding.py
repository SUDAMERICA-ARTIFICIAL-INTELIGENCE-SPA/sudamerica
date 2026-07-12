"""Onboarding chat route — api_execute owns the registration prompt,
open_agent (mode `generate`, no tools) provides the LLM brain."""

import json
import logging
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends

from app.config import ApiExecuteSettings
from app.prompts_ai import registro_de_usuarios
from app.routes.deps import get_settings
from app.schemas.onboarding import OnboardingChatRequest, OnboardingChatResponse
from shared.middleware import build_service_auth_headers
from shared.rubros import resolve_rubro
from shared.utils.http_client import internal_http

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

_FALLBACK_REPLY = OnboardingChatResponse(
    reply="Lo siento, estoy teniendo problemas tecnicos. Intenta de nuevo en unos segundos.",
)


def _parse_ai_response(data: dict) -> OnboardingChatResponse | None:
    """Parse the generation response into an OnboardingChatResponse.

    Expects the LLM's JSON text under the ``content`` key (the route adapts
    open_agent's ``response`` field into that shape). Returns None if parsing
    fails.
    """
    raw_content = data.get("content", "{}")
    tokens = data.get("tokens_used", 0)
    parsed = json.loads(raw_content)

    reply = parsed.get("reply", "No entendi bien, podrias repetirlo?")
    raw_extracted = parsed.get("extractedData", {})
    _placeholders = ("...", "formal|casual|mixto", "casual|formal|mixto")
    extracted = {
        k: v for k, v in raw_extracted.items()
        if isinstance(v, str) and v.strip() and v not in _placeholders
    }
    complete = parsed.get("complete", False)
    input_type = parsed.get("inputType", "text")
    if input_type not in ("text", "password"):
        input_type = "text"

    logger.info(
        "[onboarding] <- open_agent OK | tokens=%d | extracted=%s | complete=%s",
        tokens, list(extracted.keys()) if extracted else "none", complete,
    )
    return OnboardingChatResponse(
        reply=reply, extractedData=extracted, complete=complete, inputType=input_type,
    )


def _split_conversation(llm_messages: list[dict]) -> tuple[str, list[dict]]:
    """Split [system, *turns] into (latest_user_message, prior_history).

    open_agent's /generate takes the system prompt separately plus a single
    `message` and prior `history`. The frontend always appends the user's newest
    text last, so the final turn is the current message. Falls back to a greeting
    seed when the conversation is empty (generate requires a non-empty message).
    """
    turns = llm_messages[1:]  # drop the system message
    if not turns:
        return "Hola", []
    latest = turns[-1].get("content") or "Hola"
    return latest, turns[:-1]


def _build_generate_request(
    settings: ApiExecuteSettings,
    system_prompt: str,
    message: str,
    history: list[dict],
) -> dict:
    """Build the request payload and headers for open_agent /generate."""
    payload = {
        "system_prompt": system_prompt,
        "message": message,
        "history": history,
    }
    headers = build_service_auth_headers(
        service_name="api_execute",
        audience="open_agent",
        tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
        secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        scopes=("generate:chat",),
        expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )
    url = f"{settings.SERVICE_OPEN_AGENT_URL}/api/v1/agent/generate"
    return {"url": url, "payload": payload, "headers": headers}


def _build_llm_messages(
    system_prompt: str,
    chat_history: list[dict],
) -> list[dict[str, str]]:
    """Build messages array for the LLM call."""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
    ]
    for msg in chat_history:
        role = "assistant" if msg.get("role") == "bot" else "user"
        messages.append({"role": role, "content": msg.get("text", "")})
    return messages


@router.post("/chat", response_model=OnboardingChatResponse)
async def onboarding_chat(
    body: OnboardingChatRequest,
    settings: ApiExecuteSettings = Depends(get_settings),
):
    """Onboarding conversacional: api_execute arma el prompt de registro y
    genera la respuesta vía open_agent."""
    datos = body.currentData or {}
    logger.info(
        "[onboarding] Request | msgs=%d | datos_recopilados=%s",
        len(body.messages),
        list(datos.keys()) if datos else "ninguno",
    )

    rubro = resolve_rubro({"rubro": body.rubro})
    system_prompt = registro_de_usuarios(datos_actuales=datos or None, rubro=rubro)
    messages = _build_llm_messages(
        system_prompt,
        [m.model_dump() for m in body.messages],
    )
    latest_message, history = _split_conversation(messages)

    req = _build_generate_request(settings, system_prompt, latest_message, history)
    logger.info("[onboarding] -> open_agent %s | total_msgs=%d", req["url"], len(messages))

    try:
        resp = await internal_http.post(
            req["url"], json=req["payload"], headers=req["headers"], timeout=35.0,
        )
        resp.raise_for_status()
    except httpx.ConnectError as exc:
        logger.error("[onboarding] open_agent connection failed: %s", exc)
        return _FALLBACK_REPLY
    except httpx.HTTPStatusError as exc:
        logger.error("[onboarding] open_agent HTTP %d: %s", exc.response.status_code, exc.response.text[:300])
        return _FALLBACK_REPLY
    except httpx.RequestError as exc:
        logger.error("[onboarding] open_agent request error: %s", exc)
        return _FALLBACK_REPLY

    try:
        gen = resp.json()
        # Adapt GenerateResponse{response, tokens_used, model_used} into the shape
        # _parse_ai_response expects: the LLM's JSON text under `content`.
        adapted = {"content": gen.get("response", "{}"), "tokens_used": gen.get("tokens_used", 0)}
        result = _parse_ai_response(adapted)
        return result if result else _FALLBACK_REPLY
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("[onboarding] Parse error: %s", exc)
        return _FALLBACK_REPLY
