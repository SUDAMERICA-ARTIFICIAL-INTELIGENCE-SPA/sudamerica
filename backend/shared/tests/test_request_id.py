import json
import uuid

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.testclient import TestClient

from shared.middleware.request_id import RequestIdMiddleware, get_request_id
from shared.middleware.request_logging import RequestLoggingMiddleware
from shared.utils.logging import get_logger


def create_test_app():
    app = FastAPI()
    logger = get_logger("test-service", level="INFO")

    class TenantStubMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.tenant_id = "tenant-123"
            return await call_next(request)

    # Middleware order: last added runs first
    app.add_middleware(RequestLoggingMiddleware, service_name="test-service", logger=logger)
    app.add_middleware(TenantStubMiddleware)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True, "request_id": get_request_id()}

    return app


def parse_logs(captured_output: str):
    lines = [line for line in captured_output.splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def test_generates_request_id_when_missing(capsys):
    app = create_test_app()
    client = TestClient(app)

    resp = client.get("/ping")
    rid = resp.headers.get("X-Request-ID")

    assert rid is not None
    uuid.UUID(rid)  # validates format

    logs = parse_logs(capsys.readouterr().out)
    ids = {log["request_id"] for log in logs}
    assert rid in ids


def test_propagates_request_id_header(capsys):
    app = create_test_app()
    client = TestClient(app)
    custom_rid = "abc-123-custom"

    resp = client.get("/ping", headers={"X-Request-ID": custom_rid})
    assert resp.headers["X-Request-ID"] == custom_rid

    logs = parse_logs(capsys.readouterr().out)
    assert any(log["request_id"] == custom_rid for log in logs)


def test_logger_emits_json_with_tenant_and_duration(capsys):
    app = create_test_app()
    client = TestClient(app)
    client.get("/ping")

    logs = parse_logs(capsys.readouterr().out)
    completed = next(log for log in logs if log["message"] == "request completed")

    assert completed["tenant_id"] == "tenant-123"
    assert completed["path"] == "/ping"
    assert completed["method"] == "GET"
    assert completed["status_code"] == 200
    assert isinstance(completed["duration_ms"], int)
    assert completed["duration_ms"] >= 0


def test_logger_outside_request_has_placeholder_request_id(capsys):
    logger = get_logger("test-service-outside", level="INFO")
    logger.info("background task", extra={"extra": {"job": "sync"}})

    logs = parse_logs(capsys.readouterr().out)
    log = logs[-1]
    assert log["request_id"] == "no-request"
    assert log["extra"] == {"job": "sync"}
    assert log["message"] == "background task"


def test_response_includes_header(capsys):
    app = create_test_app()
    client = TestClient(app)
    resp = client.get("/ping", headers={"X-Request-ID": "req-999"})
    assert resp.headers["X-Request-ID"] == "req-999"

    logs = parse_logs(capsys.readouterr().out)
    assert any(log["request_id"] == "req-999" for log in logs)
