"""Enums used across all microservices — matching PDF spec."""

from enum import Enum


class UserRole(str, Enum):
    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"
    GERENTE = "GERENTE"        # branch manager — full ops for assigned sucursal
    MESERO = "MESERO"          # waiter — comandas/mesas in assigned sucursal
    COCINA = "COCINA"          # kitchen — KDS only in assigned sucursal
    CAJA = "CAJA"              # cashier — ventas/cobros in assigned sucursal
    PERSONAL = "PERSONAL"      # legacy generic staff role
    ASESOR = "ASESOR"          # deprecated, maps to PERSONAL
    VIEWER = "VIEWER"          # read-only across all sucursales


class TenantPlan(str, Enum):
    ESTANDAR = "ESTANDAR"
    PLUS = "PLUS"
    PRO = "PRO"
    FREE = "FREE"  # deprecated, maps to ESTANDAR

    @property
    def max_users(self) -> int:
        return {
            TenantPlan.ESTANDAR: 3,
            TenantPlan.FREE: 3,
            TenantPlan.PLUS: 8,
            TenantPlan.PRO: 20,
        }[self]

    @property
    def max_leads_mes(self) -> int:
        return {
            TenantPlan.ESTANDAR: 100,
            TenantPlan.FREE: 100,
            TenantPlan.PLUS: 500,
            TenantPlan.PRO: 999_999,
        }[self]


class LeadCanal(str, Enum):
    WHATSAPP = "WHATSAPP"
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"
    WEB = "WEB"
    TELEFONO = "TELEFONO"
    EMAIL = "EMAIL"
    REFERIDO = "REFERIDO"


class LeadEstado(str, Enum):
    NUEVO = "NUEVO"
    CONTACTADO = "CONTACTADO"
    EN_PROCESO = "EN_PROCESO"
    CONVERTIDO = "CONVERTIDO"
    DESCARTADO = "DESCARTADO"

    @classmethod
    def valid_transitions(cls) -> dict[str, list[str]]:
        return {
            cls.NUEVO: [cls.CONTACTADO, cls.DESCARTADO],
            cls.CONTACTADO: [cls.EN_PROCESO, cls.DESCARTADO],
            cls.EN_PROCESO: [cls.CONVERTIDO, cls.DESCARTADO],
            cls.CONVERTIDO: [],
            cls.DESCARTADO: [],
        }

    def can_transition_to(self, target: "LeadEstado") -> bool:
        return target in self.valid_transitions().get(self, [])


class RevisionAccion(str, Enum):
    APROBAR = "APROBAR"
    EDITAR = "EDITAR"
    RECHAZAR = "RECHAZAR"


class RevisionDeliveryStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class SubAgenteType(str, Enum):
    RAG = "RAG"
    COTIZADOR = "COTIZADOR"
    SEGUIMIENTO = "SEGUIMIENTO"
    FAQ = "FAQ"


class TipoEntrega(str, Enum):
    MESA = "MESA"
    DELIVERY = "DELIVERY"
    RETIRO = "RETIRO"


class CanalOrigen(str, Enum):
    WHATSAPP = "WHATSAPP"
    WEB = "WEB"
    PRESENCIAL = "PRESENCIAL"


class ComandaEstado(str, Enum):
    PENDIENTE = "PENDIENTE"
    EN_COCINA = "EN_COCINA"
    # F4 multi-rubro: fase de preparación genérica (rubros sin cocina). No aparece en
    # valid_transitions (FSM restaurante); el FSM real por rubro vive en
    # shared/rubros/operativa.py y lo consulta comanda_svc.transition_estado.
    EN_PROCESO = "EN_PROCESO"
    LISTO = "LISTO"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"

    @classmethod
    def valid_transitions(cls) -> dict[str, list[str]]:
        return {
            cls.PENDIENTE: [cls.EN_COCINA, cls.CANCELADO],
            cls.EN_COCINA: [cls.LISTO, cls.CANCELADO],
            cls.LISTO: [cls.ENTREGADO, cls.CANCELADO],
            cls.ENTREGADO: [],
            cls.CANCELADO: [],
        }

    def can_transition_to(self, target: "ComandaEstado") -> bool:
        return target in self.valid_transitions().get(self, [])


class ModifierGroupTipo(str, Enum):
    SINGLE_SELECT = "SINGLE_SELECT"
    MULTI_SELECT = "MULTI_SELECT"


class ClienteEstado(str, Enum):
    NUEVO = "NUEVO"
    OCASIONAL = "OCASIONAL"
    FRECUENTE = "FRECUENTE"
    VIP = "VIP"
    INACTIVO = "INACTIVO"


class DeliveryEstado(str, Enum):
    PUBLICADO = "PUBLICADO"
    ACEPTADO = "ACEPTADO"
    EN_RUTA = "EN_RUTA"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"

    @classmethod
    def valid_transitions(cls) -> dict[str, list[str]]:
        return {
            cls.PUBLICADO: [cls.ACEPTADO, cls.CANCELADO],
            cls.ACEPTADO: [cls.EN_RUTA, cls.CANCELADO],
            cls.EN_RUTA: [cls.ENTREGADO, cls.CANCELADO],
            cls.ENTREGADO: [],
            cls.CANCELADO: [],
        }

    def can_transition_to(self, target: "DeliveryEstado") -> bool:
        return target in self.valid_transitions().get(self, [])


class MetodoPago(str, Enum):
    TRANSFERENCIA = "TRANSFERENCIA"
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    CONTRA_ENTREGA = "CONTRA_ENTREGA"
