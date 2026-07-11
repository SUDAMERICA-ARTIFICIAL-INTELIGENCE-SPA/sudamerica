"""All Pydantic schemas for api_execute."""

from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate
from app.schemas.usuario import UsuarioCreate, UsuarioResponse, UsuarioUpdate
from app.schemas.categoria import CategoriaCreate, CategoriaResponse, CategoriaUpdate
from app.schemas.producto import (
    ProductoCreate,
    ProductoFilter,
    ProductoResponse,
    ProductoUpdate,
)
from app.schemas.lead import LeadCreate, LeadResponse, LeadTransicion, LeadUpdate
from app.schemas.venta import VentaCreate, VentaResponse
from app.schemas.metrica import (
    DashboardKpis,
    MetricaConversion,
    MetricaLeadEstado,
    MetricaPorCanal,
    MetricaPorSector,
    MetricaProductoTop,
    MetricaRevenue,
    RevenueDataPoint,
)
from app.schemas.smart_alert import SmartAlertResponse, SmartAlertUpdate
from app.schemas.sales_target import SalesTargetCreate, SalesTargetResponse

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    "UsuarioCreate",
    "UsuarioUpdate",
    "UsuarioResponse",
    "CategoriaCreate",
    "CategoriaUpdate",
    "CategoriaResponse",
    "ProductoCreate",
    "ProductoUpdate",
    "ProductoResponse",
    "ProductoFilter",
    "LeadCreate",
    "LeadUpdate",
    "LeadTransicion",
    "LeadResponse",
    "VentaCreate",
    "VentaResponse",
    "MetricaRevenue",
    "MetricaPorCanal",
    "MetricaPorSector",
    "MetricaProductoTop",
    "MetricaConversion",
    "MetricaLeadEstado",
    "DashboardKpis",
    "RevenueDataPoint",
    "SmartAlertResponse",
    "SmartAlertUpdate",
    "SalesTargetCreate",
    "SalesTargetResponse",
]
