"""Operativa por rubro (F4 multi-rubro): estados de orden y roles de equipo.

Módulo PURO derivado del diccionario: estados/roles NO se configuran a mano por rubro,
se derivan de sus módulos (COMANDAS_KDS ⇒ fase de cocina; RECURSO ⇒ rol de sala).
Restaurante reproduce EXACTAMENTE el FSM actual de ``ComandaEstado.valid_transitions``
y el set completo de roles (byte-idéntico; test de sincronización en test_operativa).
"""

from __future__ import annotations

from typing import Mapping

from shared.rubros.capacidades import Capacidad
from shared.rubros.diccionario import Primitiva, rubro_def

PENDIENTE = "PENDIENTE"
EN_COCINA = "EN_COCINA"
EN_PROCESO = "EN_PROCESO"  # fase de preparación genérica (rubros sin cocina)
LISTO = "LISTO"
ENTREGADO = "ENTREGADO"
CANCELADO = "CANCELADO"

_TRANSICIONES_COCINA: Mapping[str, tuple[str, ...]] = {
    PENDIENTE: (EN_COCINA, CANCELADO),
    EN_COCINA: (LISTO, CANCELADO),
    LISTO: (ENTREGADO, CANCELADO),
    ENTREGADO: (),
    CANCELADO: (),
}

# Sin cocina la preparación es opcional: PENDIENTE puede saltar directo a LISTO.
_TRANSICIONES_GENERICAS: Mapping[str, tuple[str, ...]] = {
    PENDIENTE: (EN_PROCESO, LISTO, CANCELADO),
    EN_PROCESO: (LISTO, CANCELADO),
    LISTO: (ENTREGADO, CANCELADO),
    ENTREGADO: (),
    CANCELADO: (),
}


def transiciones_orden(rubro_key: str) -> Mapping[str, tuple[str, ...]]:
    """FSM de estados de la orden para el rubro (restaurante = FSM clásico)."""
    if rubro_def(rubro_key).tiene_capacidad(Capacidad.MESAS):
        return _TRANSICIONES_COCINA
    return _TRANSICIONES_GENERICAS


def estados_orden(rubro_key: str) -> tuple[str, ...]:
    """Estados válidos de la orden para el rubro."""
    return tuple(transiciones_orden(rubro_key))


def puede_transicionar(rubro_key: str, actual: str, objetivo: str) -> bool:
    """True si la transición ``actual → objetivo`` es válida en el FSM del rubro."""
    return objetivo in transiciones_orden(rubro_key).get(actual, ())


# ── Roles de equipo por rubro (superset ya existente en UserRole; sin migración) ──

_ROLES_BASE: tuple[str, ...] = ("SUPERADMIN", "ADMIN", "GERENTE", "CAJA", "PERSONAL", "VIEWER")
_ROL_SALA = "MESERO"    # requiere flag `recurso` (atención en sala/recurso físico)
_ROL_COCINA = "COCINA"  # requiere capacidad MESAS (cocina/salón)


def roles_equipo(rubro_key: str) -> tuple[str, ...]:
    """Roles aplicables al rubro; restaurante conserva el set completo actual."""
    r = rubro_def(rubro_key)
    roles = list(_ROLES_BASE)
    if r.recurso:
        roles.append(_ROL_SALA)
    if r.tiene_capacidad(Capacidad.MESAS):
        roles.append(_ROL_COCINA)
    return tuple(roles)


# ── Recurso físico reservable (F5, fase expand) ──────────────────────────────


def tipo_recurso_default(rubro_key: str) -> str:
    """Tipo del recurso reservable del rubro (columna ``mesas.tipo``): mesa/silla/…"""
    return rubro_def(rubro_key).labels[Primitiva.RECURSO].lower()
