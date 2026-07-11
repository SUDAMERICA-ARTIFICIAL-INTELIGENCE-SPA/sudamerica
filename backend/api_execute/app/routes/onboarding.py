"""Onboarding chat route — api_execute owns the registration prompt,
AI_dialer provides the LLM brain."""

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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

_FALLBACK_REPLY = OnboardingChatResponse(
    reply="Lo siento, estoy teniendo problemas tecnicos. Intenta de nuevo en unos segundos.",
)


def _parse_ai_response(data: dict) -> OnboardingChatResponse | None:
    """Parse the AI_dialer response into an OnboardingChatResponse.

    Returns None if parsing fails.
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
        "[onboarding] <- AI_dialer OK | tokens=%d | extracted=%s | complete=%s",
        tokens, list(extracted.keys()) if extracted else "none", complete,
    )
    return OnboardingChatResponse(
        reply=reply, extractedData=extracted, complete=complete, inputType=input_type,
    )


def _build_ai_dialer_request(settings: ApiExecuteSettings, messages: list[dict]) -> dict:
    """Build the request payload and headers for AI_dialer."""
    payload = {"messages": messages, "response_format": "json"}
    headers = build_service_auth_headers(
        service_name="api_execute",
        audience="ai_dialer",
        tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
        secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        scopes=("onboarding:chat",),
        expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )
    url = f"{settings.SERVICE_AI_DIALER_URL}/api/v1/ai/onboarding-chat"
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
    """Onboarding conversacional: api_execute envia el prompt de registro
    al AI_dialer para que procese con el LLM."""
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

    req = _build_ai_dialer_request(settings, messages)
    logger.info("[onboarding] -> AI_dialer %s | total_msgs=%d", req["url"], len(messages))

    from shared.utils.http_client import internal_http

    try:
        resp = await internal_http.post(
            req["url"], json=req["payload"], headers=req["headers"], timeout=35.0,
        )
        resp.raise_for_status()
    except httpx.ConnectError as exc:
        logger.error("[onboarding] AI_dialer connection failed: %s", exc)
        return _FALLBACK_REPLY
    except httpx.HTTPStatusError as exc:
        logger.error("[onboarding] AI_dialer HTTP %d: %s", exc.response.status_code, exc.response.text[:300])
        return _FALLBACK_REPLY
    except httpx.RequestError as exc:
        logger.error("[onboarding] AI_dialer request error: %s", exc)
        return _FALLBACK_REPLY

    try:
        result = _parse_ai_response(resp.json())
        return result if result else _FALLBACK_REPLY
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("[onboarding] Parse error: %s", exc)
        return _FALLBACK_REPLY
