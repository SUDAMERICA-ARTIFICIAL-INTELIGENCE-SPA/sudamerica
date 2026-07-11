"""Health check utilities shared across microservices.

Two probe levels:
  /health       — liveness (no IO, <10ms)
  /health/ready — readiness (checks all dependencies in parallel)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class DependencyCheck:
    name: str
    healthy: bool
    latency_ms: float
    detail: str = ""


@dataclass
class HealthReport:
    status: str  # "healthy" | "degraded" | "unhealthy"
    service: str
    checks: list[DependencyCheck] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "service": self.service,
            "checks": [
                {
                    "name": c.name,
                    "healthy": c.healthy,
                    "latency_ms": round(c.latency_ms, 1),
                    **({"detail": c.detail} if c.detail else {}),
                }
                for c in self.checks
            ],
        }


async def check_database(session_factory) -> DependencyCheck:
    """Verify database connectivity with ``SELECT 1``."""
    from sqlalchemy import text

    start = time.perf_counter()
    try:
        async with session_factory() as db:
            await db.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        return DependencyCheck(name="database", healthy=True, latency_ms=latency)
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        logger.error("Database health check failed: %s", exc)
        return DependencyCheck(
            name="database", healthy=False, latency_ms=latency,
            detail=str(exc)[:200],
        )


async def check_service(url: str, name: str, *, timeout: float = 5.0) -> DependencyCheck:
    """Verify a downstream service responds to ``GET /health``."""
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{url}/health")
            latency = (time.perf_counter() - start) * 1000
            healthy = resp.status_code == 200
            return DependencyCheck(
                name=name, healthy=healthy, latency_ms=latency,
                detail="" if healthy else f"status={resp.status_code}",
            )
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        logger.warning("Service %s health check failed: %s", name, exc)
        return DependencyCheck(
            name=name, healthy=False, latency_ms=latency,
            detail=type(exc).__name__,
        )


async def check_evolution_api(url: str, api_key: str) -> DependencyCheck:
    """Check Evolution API connectivity via ``/instance/fetchInstances``."""
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{url}/instance/fetchInstances",
                headers={"apikey": api_key},
            )
            latency = (time.perf_counter() - start) * 1000
            healthy = resp.status_code == 200
            return DependencyCheck(
                name="evolution-api", healthy=healthy, latency_ms=latency,
                detail="" if healthy else f"status={resp.status_code}",
            )
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        return DependencyCheck(
            name="evolution-api", healthy=False, latency_ms=latency,
            detail=type(exc).__name__,
        )


async def build_health_report(
    service_name: str,
    checks: list,
) -> HealthReport:
    """Run all check coroutines concurrently and build a report."""
    results = await asyncio.gather(*checks, return_exceptions=True)

    parsed: list[DependencyCheck] = []
    for r in results:
        if isinstance(r, DependencyCheck):
            parsed.append(r)
        elif isinstance(r, Exception):
            parsed.append(DependencyCheck(
                name="unknown", healthy=False, latency_ms=0,
                detail=str(r)[:200],
            ))

    all_healthy = all(c.healthy for c in parsed)
    any_healthy = any(c.healthy for c in parsed)

    if all_healthy:
        status = "healthy"
    elif any_healthy:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthReport(service=service_name, status=status, checks=parsed)
