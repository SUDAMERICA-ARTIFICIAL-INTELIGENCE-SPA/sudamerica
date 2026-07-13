"""Schemas de lentes derivadas de OLA A (B1): cobros, tesorería, flujo de caja, actividad, kardex."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class CobroPorMetodo(BaseModel):
    metodo: str
    cobrado: Decimal = Decimal("0")
    pendiente: Decimal = Decimal("0")
    pedidos: int = 0


class CobroPendiente(BaseModel):
    comanda_id: UUID
    cliente: str | None = None
    monto: Decimal
    metodo: str | None = None
    estado: str
    fecha: datetime


class CobrosResumen(BaseModel):
    total_cobrado: Decimal = Decimal("0")
    total_pendiente: Decimal = Decimal("0")
    pedidos_cobrados: int = 0
    pedidos_pendientes: int = 0
    por_metodo: list[CobroPorMetodo] = []
    pendientes_recientes: list[CobroPendiente] = []


class SaldoMetodo(BaseModel):
    metodo: str
    saldo: Decimal = Decimal("0")
    movimientos: int = 0


class Tesoreria(BaseModel):
    saldo_total: Decimal = Decimal("0")
    por_metodo: list[SaldoMetodo] = []


class FlujoPunto(BaseModel):
    periodo: str
    ingresos: Decimal = Decimal("0")
    egresos: Decimal = Decimal("0")
    neto: Decimal = Decimal("0")


class ActividadItem(BaseModel):
    tipo: str            # VENTA / LEAD / PEDIDO / CONVERSACION
    titulo: str
    subtitulo: str | None = None
    monto: Decimal | None = None
    fecha: datetime


class MovimientoKardex(BaseModel):
    fecha: datetime
    tipo: str            # ENTRADA / SALIDA
    producto: str | None = None
    producto_id: UUID | None = None
    cantidad: Decimal
    costo_unitario: Decimal | None = None
    referencia: str | None = None
