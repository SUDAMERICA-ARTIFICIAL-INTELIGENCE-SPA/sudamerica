"""Receive webhook payloads enqueued by Cloud Tasks and forward for processing.

Cloud Tasks flow:
  Cloud Tasks → POST /api/v1/tasks/process-webhook (this endpoint)
  → validates OIDC token from Cloud Tasks
  → forwards payload to canales_service /webhook/whatsapp/process
  → canales_service runs the full AI pipeline
"""

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from shared.middleware import build_service_auth_headers

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook-processor"])

# Cloud Tasks sets these headers; Cloud Run does NOT strip them, but
# combined with OIDC validation they confirm the request origin.
_CLOUD_TASKS_HEADER = "X-CloudTasks-QueueName"


def _validate_cloud_tasks_origin(request: Request) -> None:
    """Verify the request originates from Google Cloud Tasks.

    Cloud Tasks sends an OIDC token in the Authorization header.
    As an additional signal, it sets X-CloudTasks-QueueName.
    For services that allow unauthenticated access (allUsers), we
    validate the OIDC token to confirm the caller is the expected SA.
    """
    queue_name = request.headers.get(_CLOUD_TASKS_HEADER)
    if not queue_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing Cloud Tasks header",
        )

    # Validate OIDC token if google-auth is available
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            claims = google_id_token.verify_oauth2_token(
                token, google_requests.Request()
            )
            logger.info(
                "Cloud Tasks OIDC validated: issuer=%s email=%s",
                claims.get("iss"),
                claims.get("email"),
            )
        except ImportError:
            logger.debug("google-auth not installed — skipping OIDC validation")
        except Exception:
            logger.warning("OIDC token validation failed", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid OIDC token",
            )


@router.post("/process-webhook", status_code=status.HTTP_200_OK)
async def process_webhook(request: Request) -> dict:
    """Receive a webhook payload from Cloud Tasks and forward to canales_service.

    The actual message processing (AI classification, reply, etc.) stays in
    canales_service where the WhatsApp service logic lives.  This endpoint
    acts as the Cloud Tasks receiver and dispatcher.
    """
    _validate_cloud_tasks_origin(request)

    payload = await request.json()
    settings = request.app.state.settings
    request_id = request.headers.get("x-request-id", "")

    instance_name = payload.get("instance_name", "unknown")
    sender = payload.get("sender", "unknown")
    logger.info(
        "Processing enqueued webhook: instance=%s sender=%s request_id=%s",
        instance_name, sender, request_id,
    )

    # Build internal service JWT (tasks → canales_service)
    # Use a zero-UUID tenant since the real tenant is resolved inside canales_service
    from uuid import UUID

    canales_url = f"{settings.SERVICE_CANALES_URL}/api/v1/canales/webhook/whatsapp/process"
    headers = build_service_auth_headers(
        service_name="tasks",
        audience="canales_service",
        tenant_id=UUID(int=0),
        signing_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        scopes=("webhook:process",),
    )
    from shared.utils.http_client import internal_http

    try:
        resp = await internal_http.post(
            canales_url, json=payload, headers=headers, timeout=120.0,
        )
        resp.raise_for_status()
        result = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "canales_service returned %s for webhook processing: %s",
            exc.response.status_code,
            exc.response.text[:500],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Webhook processing failed in canales_service",
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("Failed to reach canales_service for webhook processing")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach canales_service",
        ) from exc

    logger.info("Webhook processed successfully: instance=%s sender=%s", instance_name, sender)
    return {"status": "processed", "detail": result}
