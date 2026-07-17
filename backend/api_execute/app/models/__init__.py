"""All SQLAlchemy models for api_execute."""

from app.models.tenant import Tenant
from app.models.usuario import Usuario
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.lead import Lead
from app.models.venta import Venta
from shared.models.mesa import Mesa
from app.models.stripe_event import StripeEvent
from app.models.smart_alert import SmartAlert
from app.models.sales_target import SalesTarget
from app.models.comanda import Comanda, ComandaItem
from app.models.delivery import DeliveryAssignment, Repartidor
from app.models.modifier import Modifier, ModifierGroup, ProductoModifierGroup
from app.models.password_reset_token import PasswordResetToken
from app.models.suministro import Receta, Suministro
from app.models.menu_import import MenuImport
from app.models.compras import (
    Cotizacion,
    FacturaProveedor,
    OCItem,
    OrdenCompra,
    Proveedor,
    Recepcion,
    RecepcionItem,
    Requisicion,
)
from app.models.olab_crud import Campana, DocumentoArchivo, Devolucion, MensajePlantilla
from shared.models.sucursal import Sucursal

__all__ = [
    "Tenant",
    "Usuario",
    "Categoria",
    "Producto",
    "Lead",
    "Venta",
    "Mesa",
    "MenuImport",
    "StripeEvent",
    "SmartAlert",
    "SalesTarget",
    "Comanda",
    "ComandaItem",
    "DeliveryAssignment",
    "Modifier",
    "ModifierGroup",
    "ProductoModifierGroup",
    "PasswordResetToken",
    "Receta",
    "Repartidor",
    "Sucursal",
    "Suministro",
    "Proveedor",
    "OrdenCompra",
    "OCItem",
    "Recepcion",
    "RecepcionItem",
    "FacturaProveedor",
    "Requisicion",
    "Cotizacion",
    "Devolucion",
    "MensajePlantilla",
    "DocumentoArchivo",
    "Campana",
]
