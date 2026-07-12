"""Catálogo de capacidades (ERP+CRM) — categorización nueva de los rubros.

22 capacidades = las 20 del artifact "Sidebar · 3 propuestas para 100+ rubros" + 2
nuevas ERP (``compras``, ``produccion``) decididas en Fase 0 (vacíos ERP §1.3 del
superprompt). La capacidad es la unidad de la categorización ``rubro → capacidades``
y del gating del árbol de navegación; es agnóstica de la taxonomía de sidebar.

El campo ``capacidades`` STORED en cada ``Rubro`` es el canónico (curado por rubro,
Fase 2). La derivación §3 desde los módulos viejos cumplió su rol de semilla y se
retiró junto con ``modulos`` en la Etapa B (los modos de dato `recurso`/`variantes`/
`precio_medida` viven como flags del ``Rubro``).

Puro (sin ORM), igual que ``diccionario.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


class Capacidad:
    """Slugs canónicos de las 22 capacidades (ERP+CRM)."""

    CATALOGO = "catalogo"
    AGENDA = "agenda"
    COTIZADOR = "cotizador"
    PEDIDOS = "pedidos"
    PAGOS = "pagos"
    DELIVERY = "delivery"
    SUSCRIPCIONES = "suscripciones"
    SOPORTE = "soporte"
    PROYECTOS = "proyectos"
    INVENTARIO = "inventario"
    COMPRAS = "compras"
    PRODUCCION = "produccion"
    EXPEDIENTES = "expedientes"
    CONTRATOS = "contratos"
    CURSOS = "cursos"
    ARRIENDOS = "arriendos"
    FACTURACION = "facturacion"
    FIDELIZACION = "fidelizacion"
    CAMPANAS = "campanas"
    TERRENO = "terreno"
    MESAS = "mesas"
    CONSENTIMIENTOS = "consentimientos"
    CONTABILIDAD = "contabilidad"
    ACTIVOS_FIJOS = "activos_fijos"
    RRHH = "rrhh"


# Orden canónico (CAP_ORDER): las tuplas `capacidades` de cada rubro se guardan en
# este orden en AMBOS SSOT (Py y TS) para que el espejo sea determinista.
CAPACIDADES: tuple[str, ...] = (
    Capacidad.CATALOGO,
    Capacidad.AGENDA,
    Capacidad.COTIZADOR,
    Capacidad.PEDIDOS,
    Capacidad.PAGOS,
    Capacidad.DELIVERY,
    Capacidad.SUSCRIPCIONES,
    Capacidad.SOPORTE,
    Capacidad.PROYECTOS,
    Capacidad.INVENTARIO,
    Capacidad.COMPRAS,
    Capacidad.PRODUCCION,
    Capacidad.EXPEDIENTES,
    Capacidad.CONTRATOS,
    Capacidad.CURSOS,
    Capacidad.ARRIENDOS,
    Capacidad.FACTURACION,
    Capacidad.FIDELIZACION,
    Capacidad.CAMPANAS,
    Capacidad.TERRENO,
    Capacidad.MESAS,
    Capacidad.CONSENTIMIENTOS,
    Capacidad.CONTABILIDAD,
    Capacidad.ACTIVOS_FIJOS,
    Capacidad.RRHH,
)


@dataclass(frozen=True)
class CapacidadMeta:
    """Metadata de presentación de una capacidad (label, descripción, eje)."""

    slug: str
    label: str
    descripcion: str
    eje: str


CAPACIDADES_META: Mapping[str, CapacidadMeta] = MappingProxyType(
    {
        Capacidad.CATALOGO: CapacidadMeta(
            Capacidad.CATALOGO,
            "Catálogo",
            "Productos/servicios con precios, variantes y fotos.",
            "venta",
        ),
        Capacidad.AGENDA: CapacidadMeta(
            Capacidad.AGENDA,
            "Agenda",
            "Reserva de horas, citas y turnos con recursos/profesionales.",
            "servicio",
        ),
        Capacidad.COTIZADOR: CapacidadMeta(
            Capacidad.COTIZADOR,
            "Cotizador",
            "Presupuestos configurables y su aprobación.",
            "erp",
        ),
        Capacidad.PEDIDOS: CapacidadMeta(
            Capacidad.PEDIDOS,
            "Pedidos",
            "Órdenes/comandas/órdenes de servicio y su preparación.",
            "operacion",
        ),
        Capacidad.PAGOS: CapacidadMeta(
            Capacidad.PAGOS,
            "Pagos",
            "Cobro con links, tarjetas y POS. Incluye caja: apertura/arqueo/cierre por turno.",
            "dinero",
        ),
        Capacidad.DELIVERY: CapacidadMeta(
            Capacidad.DELIVERY,
            "Delivery",
            "Despacho, reparto y seguimiento de entregas.",
            "logistica",
        ),
        Capacidad.SUSCRIPCIONES: CapacidadMeta(
            Capacidad.SUSCRIPCIONES,
            "Suscripciones",
            "Planes recurrentes, membresías, cobros automáticos.",
            "dinero",
        ),
        Capacidad.SOPORTE: CapacidadMeta(
            Capacidad.SOPORTE,
            "Soporte",
            "Tickets, casos, mesa de ayuda con SLA. Incluye garantías/RMA post-venta.",
            "crm",
        ),
        Capacidad.PROYECTOS: CapacidadMeta(
            Capacidad.PROYECTOS,
            "Proyectos",
            "Trabajos por fases, hitos y avance (incluye obras).",
            "erp",
        ),
        Capacidad.INVENTARIO: CapacidadMeta(
            Capacidad.INVENTARIO,
            "Inventario",
            "Stock, bodegas y movimientos de existencias (producto terminado).",
            "erp",
        ),
        Capacidad.COMPRAS: CapacidadMeta(
            Capacidad.COMPRAS,
            "Compras",
            "Órdenes de compra, proveedores, recepción de mercadería y cuentas por pagar.",
            "erp",
        ),
        Capacidad.PRODUCCION: CapacidadMeta(
            Capacidad.PRODUCCION,
            "Producción",
            "Recetas/BOM, consumo de insumos, órdenes de producción y costeo.",
            "erp",
        ),
        Capacidad.EXPEDIENTES: CapacidadMeta(
            Capacidad.EXPEDIENTES,
            "Expedientes",
            "Fichas e historial de cliente/paciente/caso.",
            "crm_salud",
        ),
        Capacidad.CONTRATOS: CapacidadMeta(
            Capacidad.CONTRATOS,
            "Contratos",
            "Documentos, firma y control de vigencias.",
            "erp_legal",
        ),
        Capacidad.CURSOS: CapacidadMeta(
            Capacidad.CURSOS,
            "Cursos",
            "Programas, clases, inscripción y asistencia.",
            "educacion",
        ),
        Capacidad.ARRIENDOS: CapacidadMeta(
            Capacidad.ARRIENDOS,
            "Arriendos",
            "Alquiler de activos y calendario de disponibilidad.",
            "erp",
        ),
        Capacidad.FACTURACION: CapacidadMeta(
            Capacidad.FACTURACION,
            "Facturación",
            "Documentos tributarios (boleta/factura/DTE, notas de crédito). Incluye "
            "cuentas por cobrar/crédito B2B y facturación previsional salud (bono/reembolso).",
            "erp",
        ),
        Capacidad.FIDELIZACION: CapacidadMeta(
            Capacidad.FIDELIZACION,
            "Fidelización",
            "Puntos, sellos, niveles y recompensas.",
            "crm",
        ),
        Capacidad.CAMPANAS: CapacidadMeta(
            Capacidad.CAMPANAS,
            "Campañas",
            "Difusión y mensajería masiva a segmentos.",
            "crm",
        ),
        Capacidad.TERRENO: CapacidadMeta(
            Capacidad.TERRENO,
            "Terreno",
            "Visitas, rutas y técnicos en terreno.",
            "erp",
        ),
        Capacidad.MESAS: CapacidadMeta(
            Capacidad.MESAS,
            "Mesas",
            "Gestión de mesas, aforo y sala.",
            "gastronomia",
        ),
        Capacidad.CONSENTIMIENTOS: CapacidadMeta(
            Capacidad.CONSENTIMIENTOS,
            "Consentimientos",
            "Formularios y consentimientos firmados.",
            "salud_legal",
        ),
        Capacidad.CONTABILIDAD: CapacidadMeta(
            Capacidad.CONTABILIDAD,
            "Contabilidad",
            "Plan de cuentas, asientos, libro mayor, CxC/CxP, conciliación y estados financieros.",
            "erp",
        ),
        Capacidad.ACTIVOS_FIJOS: CapacidadMeta(
            Capacidad.ACTIVOS_FIJOS,
            "Activos fijos",
            "Registro, depreciación, mantenciones y bajas de activos fijos.",
            "erp",
        ),
        Capacidad.RRHH: CapacidadMeta(
            Capacidad.RRHH,
            "Personas (RRHH)",
            "Empleados, contratos, asistencia, vacaciones, liquidaciones y remuneraciones.",
            "erp",
        ),
    }
)
