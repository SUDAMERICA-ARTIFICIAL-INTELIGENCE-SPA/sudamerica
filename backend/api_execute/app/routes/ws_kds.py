"""WebSocket endpoint for real-time KDS (Kitchen Display System) events."""

import asyncio
import json
import logging
from typing import Any

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# tenant_id (str) -> set of active WebSocket connections
_connections: dict[str, set[WebSocket]] = {}


async def _safe_close_websocket(websocket: WebSocket) -> None:
    """Best-effort close for sockets that are already failing."""
    try:
        await websocket.close()
    except RuntimeError:
        pass
    except Exception:
        logger.debug("Failed to close KDS WebSocket cleanly", exc_info=True)


def _unregister_connection(tenant_id: str, websocket: WebSocket) -> None:
    sockets = _connections.get(tenant_id)
    if not sockets:
        return
    sockets.discard(websocket)
    if not sockets:
        _connections.pop(tenant_id, None)


async def broadcast_kds_event(tenant_id: str, event: dict[str, Any]) -> None:
    """Send a KDS JSON event to all connected WebSockets for a given tenant.

    Event format:
        {"type": "comanda_created", "data": {...comanda_dict}}
        {"type": "comanda_updated", "data": {...comanda_dict}}
        {"type": "comanda_deleted", "data": {"id": "..."}}

    Iterates over a snapshot of the connection set so that removals during
    iteration do not cause RuntimeError.  Dead connections are cleaned up
    silently.
    """
    sockets = _connections.get(tenant_id)
    if not sockets:
        return

    payload = json.dumps(event, default=str)
    # Iterate over a copy so we can mutate the original set safely
    for ws in list(sockets):
        try:
            await ws.send_text(payload)
        except WebSocketDisconnect:
            _unregister_connection(tenant_id, ws)
        except Exception:
            logger.debug("Removing dead KDS WebSocket for tenant %s", tenant_id)
            await _safe_close_websocket(ws)
            _unregister_connection(tenant_id, ws)

    # Clean up empty sets
    if not sockets:
        _connections.pop(tenant_id, None)


def _decode_ws_token(
    token: str, secret_key: str, algorithm: str = "HS256"
) -> dict[str, Any]:
    """Decode JWT for WebSocket auth.  Raises ValueError on failure."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

    for field in ("sub", "tenant_id", "role"):
        if field not in payload:
            raise ValueError(f"Missing claim: {field}")
    return payload


async def _authenticate_ws(
    websocket: WebSocket, tenant_id: str, token: str,
) -> dict[str, Any] | None:
    """Validate JWT for KDS WebSocket. Returns payload or None (after closing)."""
    app = websocket.app
    secret_key = app.state.jwt_secret_key
    algorithm = getattr(app.state, "jwt_algorithm", "HS256")
    try:
        payload = _decode_ws_token(token, secret_key, algorithm)
    except ValueError as exc:
        await websocket.close(code=4001, reason=str(exc))
        return None
    if str(payload.get("tenant_id", "")) != tenant_id:
        await websocket.close(code=4003, reason="Tenant mismatch")
        return None
    return payload


async def _run_ws_receive_loop(websocket: WebSocket, tenant_id: str) -> None:
    """Run the ping + receive loop for an accepted KDS WebSocket."""
    ping_task = asyncio.create_task(_ping_loop(websocket))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ping_task.cancel()
        try:
            await ping_task
        except asyncio.CancelledError:
            pass


@router.websocket("/ws/kds/{tenant_id}")
async def websocket_kds_endpoint(
    websocket: WebSocket,
    tenant_id: str,
    token: str = Query(...),
) -> None:
    """Authenticated WebSocket for real-time KDS events scoped to a tenant."""
    payload = await _authenticate_ws(websocket, tenant_id, token)
    if payload is None:
        return

    await websocket.accept()
    _connections.setdefault(tenant_id, set()).add(websocket)
    logger.info("KDS WebSocket connected for tenant %s (user %s)", tenant_id, payload.get("sub"))

    try:
        await _run_ws_receive_loop(websocket, tenant_id)
    except WebSocketDisconnect:
        logger.debug("KDS WebSocket disconnected by client for tenant %s", tenant_id)
    except Exception:
        logger.debug("KDS WebSocket error for tenant %s", tenant_id, exc_info=True)
    finally:
        _unregister_connection(tenant_id, websocket)
        await _safe_close_websocket(websocket)
        logger.info("KDS WebSocket disconnected for tenant %s", tenant_id)


async def _ping_loop(ws: WebSocket) -> None:
    """Send a lightweight keepalive frame every 20s while the socket is open."""
    while True:
        await asyncio.sleep(20)
        try:
            await ws.send_json({"type": "ping"})
        except WebSocketDisconnect:
            break
        except Exception:
            break
