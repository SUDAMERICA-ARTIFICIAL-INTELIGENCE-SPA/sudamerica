"""Tests for shared.utils.health module."""

import importlib.util
import sys
from pathlib import Path

import pytest

# Import health.py directly to avoid shared.utils.__init__ import chain
# which pulls in middleware dependencies not available in all test envs.
_health_path = Path(__file__).resolve().parent.parent / "utils" / "health.py"
_spec = importlib.util.spec_from_file_location("_health", str(_health_path))
_health = importlib.util.module_from_spec(_spec)
sys.modules["_health"] = _health
_spec.loader.exec_module(_health)

DependencyCheck = _health.DependencyCheck
HealthReport = _health.HealthReport
build_health_report = _health.build_health_report


@pytest.mark.asyncio
async def test_build_health_report_all_healthy():
    """All checks pass → status='healthy'."""

    async def ok_db():
        return DependencyCheck(name="database", healthy=True, latency_ms=1.2)

    async def ok_svc():
        return DependencyCheck(name="canales-service", healthy=True, latency_ms=5.0)

    report = await build_health_report("test-svc", [ok_db(), ok_svc()])
    assert report.status == "healthy"
    assert report.service == "test-svc"
    assert len(report.checks) == 2
    assert all(c.healthy for c in report.checks)


@pytest.mark.asyncio
async def test_build_health_report_degraded():
    """One check fails, one passes → status='degraded'."""

    async def ok_db():
        return DependencyCheck(name="database", healthy=True, latency_ms=1.0)

    async def fail_svc():
        return DependencyCheck(
            name="tasks", healthy=False, latency_ms=5001.0, detail="ConnectError"
        )

    report = await build_health_report("test-svc", [ok_db(), fail_svc()])
    assert report.status == "degraded"
    assert report.checks[0].healthy is True
    assert report.checks[1].healthy is False


@pytest.mark.asyncio
async def test_build_health_report_unhealthy():
    """All checks fail → status='unhealthy'."""

    async def fail1():
        return DependencyCheck(name="database", healthy=False, latency_ms=0, detail="refused")

    async def fail2():
        return DependencyCheck(name="tasks", healthy=False, latency_ms=0, detail="timeout")

    report = await build_health_report("test-svc", [fail1(), fail2()])
    assert report.status == "unhealthy"


@pytest.mark.asyncio
async def test_build_health_report_handles_exception():
    """A check that raises is captured as unhealthy."""

    async def ok():
        return DependencyCheck(name="database", healthy=True, latency_ms=1.0)

    async def explode():
        raise RuntimeError("boom")

    report = await build_health_report("test-svc", [ok(), explode()])
    assert report.status == "degraded"
    assert report.checks[1].healthy is False
    assert "boom" in report.checks[1].detail


def test_health_report_to_dict():
    """to_dict() omits detail when empty, includes it otherwise."""
    report = HealthReport(
        status="degraded",
        service="x",
        checks=[
            DependencyCheck(name="db", healthy=True, latency_ms=1.123),
            DependencyCheck(name="svc", healthy=False, latency_ms=5000.0, detail="timeout"),
        ],
    )
    d = report.to_dict()
    assert d["status"] == "degraded"
    assert "detail" not in d["checks"][0]
    assert d["checks"][1]["detail"] == "timeout"
    assert d["checks"][0]["latency_ms"] == 1.1  # rounded to 1 decimal
