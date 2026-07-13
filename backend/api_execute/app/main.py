"""App factory for api_execute — the Orquestador principal (port 8000)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import ApiExecuteSettings
from app.routes import (
    admin_api_keys,
    admin_metrics,
    admin_rubros,
    admin_system,
    admin_tenants,
    admin_users,
    admin_whatsapp,
    ai_conversations,
    ai_dashboard,
    ai_orchestrator,
    alertas,
    auth,
    billing,
    categorias,
    comandas,
    compras,
    delivery,
    health,
    inventario,
    leads,
    loyalty,
    menu_import,
    olab_crud,
    mesa_qr,
    mesas,
    metricas,
    modifiers,
    sudamerica,
    onboarding,
    productos,
    reservaciones,
    rubros,
    sales_targets,
    stripe,
    subentidades,
    sucursales,
    suministros,
    tenants,
    usuarios,
    ventas,
    ws_kds,
)
from shared.database import create_engine, create_session_factory
from shared.middleware.request_id import RequestIdMiddleware
from shared.middleware.request_logging import RequestLoggingMiddleware
from shared.middleware.tenant import TenantMiddleware
from shared.utils import add_frontend_cors
from shared.utils.exceptions import register_exception_handlers
from shared.utils.http_client import aclose_pooled_client
from shared.utils.logging import get_logger


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = ApiExecuteSettings()
    logger = get_logger("api_execute", settings.LOG_LEVEL)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Fase B (Paso 5): carga el manifiesto de rubro desde la tabla BD al arranque. Fail-safe:
        # si la tabla está vacía/indisponible, el registro cae a diccionario.py (loggeado) y la
        # app arranca igual.
        from app.services import rubro_registry

        try:
            async with app.state.session_factory() as _db:
                await rubro_registry.load(_db)
        except Exception:
            logger.warning(
                "rubro_registry: no se pudo cargar al arranque; fallback a diccionario.py.",
                exc_info=True,
            )
        yield
        await aclose_pooled_client()
        await app.state.engine.dispose()

    app = FastAPI(
        title="Sudamérica AI Orquestador",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow frontend and local dev origins
    add_frontend_cors(app, settings.FRONTEND_URL)

    engine = create_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(engine)

    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.jwt_secret_key = settings.JWT_SECRET_KEY
    app.state.jwt_algorithm = settings.JWT_ALGORITHM
    app.state.internal_service_signing_key = settings.INTERNAL_SERVICE_SECRET_KEY
    app.state.internal_service_trusted_keys = settings.internal_service_trusted_keys
    app.state.service_name = "api_execute"
    app.state.settings = settings

    # Middleware order: last added runs first
    app.add_middleware(RequestLoggingMiddleware, service_name="api_execute", logger=logger)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1/core")
    app.include_router(tenants.router, prefix="/api/v1/core")
    app.include_router(usuarios.router, prefix="/api/v1/core")
    app.include_router(categorias.router, prefix="/api/v1/core")
    app.include_router(productos.router, prefix="/api/v1/core")
    app.include_router(leads.router, prefix="/api/v1/core")
    app.include_router(ventas.router, prefix="/api/v1/core")
    app.include_router(modifiers.router, prefix="/api/v1/core")
    app.include_router(comandas.router, prefix="/api/v1/core")
    app.include_router(delivery.router, prefix="/api/v1/core")
    app.include_router(mesas.availability_router, prefix="/api/v1")
    app.include_router(mesas.router, prefix="/api/v1/core")
    app.include_router(reservaciones.router, prefix="/api/v1/core")
    app.include_router(sucursales.router, prefix="/api/v1/core")
    app.include_router(metricas.router, prefix="/api/v1/core")
    app.include_router(ai_conversations.router, prefix="/api/v1/core")
    app.include_router(alertas.router, prefix="/api/v1/core")
    app.include_router(sales_targets.router, prefix="/api/v1/core")
    app.include_router(onboarding.router, prefix="/api/v1/core")
    app.include_router(rubros.router, prefix="/api/v1/core")
    app.include_router(ai_orchestrator.router, prefix="/api/v1/core")
    app.include_router(ai_dashboard.router, prefix="/api/v1/core")
    app.include_router(menu_import.router, prefix="/api/v1/core")
    app.include_router(stripe.router, prefix="/api/v1/core")
    app.include_router(billing.router, prefix="/api/v1/core")
    app.include_router(sudamerica.router, prefix="/api/v1/core")
    app.include_router(loyalty.router, prefix="/api/v1/core")
    app.include_router(suministros.router, prefix="/api/v1/core")
    app.include_router(subentidades.router, prefix="/api/v1/core")
    app.include_router(compras.router, prefix="/api/v1/core")
    app.include_router(inventario.router, prefix="/api/v1/core")
    app.include_router(olab_crud.router, prefix="/api/v1/core")

    # Public routes (no JWT required)
    app.include_router(mesa_qr.router, prefix="/api/v1/public")

    # Admin routes (SUPERADMIN only)
    app.include_router(admin_tenants.router, prefix="/api/v1/admin")
    app.include_router(admin_users.router, prefix="/api/v1/admin")
    app.include_router(admin_metrics.router, prefix="/api/v1/admin")
    app.include_router(admin_api_keys.router, prefix="/api/v1/admin")
    app.include_router(admin_whatsapp.router, prefix="/api/v1/admin")
    app.include_router(admin_system.router, prefix="/api/v1/admin")
    app.include_router(admin_rubros.router, prefix="/api/v1/admin")

    # WebSocket routes (no prefix — path is defined in the router)
    app.include_router(ws_kds.router)

    return app


app = create_app()
