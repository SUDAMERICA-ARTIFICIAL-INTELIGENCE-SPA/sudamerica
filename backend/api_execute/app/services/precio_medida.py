"""Precio por medida (F7 M4, módulo PRECIO_MEDIDA): helpers puros de unidad de venta.

Sin ORM ni I/O: usable desde el orquestador IA (sufijo del catálogo) y el
cotizador (subtotal por cantidad medida). ``unidad_venta='unidad'`` es el
default histórico: sin sufijo y solo cantidades enteras (restaurante byte-idéntico).
"""

from __future__ import annotations

UNIDAD_DEFAULT = "unidad"


def sufijo_unidad(unidad_venta: str | None) -> str:
    """``"/kg"``, ``"/m2"``… para unidades de medida; ``""`` para venta por unidad."""
    unidad = (unidad_venta or UNIDAD_DEFAULT).strip()
    if not unidad or unidad == UNIDAD_DEFAULT:
        return ""
    return f"/{unidad}"


def subtotal_medida(precio: float, cantidad: float, unidad_venta: str | None = None) -> float:
    """Subtotal de una línea cotizada: precio (por unidad de venta) × cantidad.

    Cantidades fraccionales (1.5 kg) solo con unidad de medida; la venta por
    unidad exige cantidad entera. Redondea a 2 decimales (moneda).
    """
    if precio < 0:
        raise ValueError("precio no puede ser negativo")
    if cantidad <= 0:
        raise ValueError("cantidad debe ser positiva")
    unidad = (unidad_venta or UNIDAD_DEFAULT).strip() or UNIDAD_DEFAULT
    if unidad == UNIDAD_DEFAULT and cantidad != int(cantidad):
        raise ValueError("cantidad fraccional requiere unidad de medida (kg, m2, …)")
    return round(precio * cantidad, 2)
