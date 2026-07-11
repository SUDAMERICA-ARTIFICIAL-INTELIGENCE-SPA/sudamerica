"""Reglas puras de inventario por artículo (F3 multi-rubro).

Módulo PURO (sin ORM/DB), testeable aislado — mismo patrón que ``rubro_prompt``.
Gobierna cuándo un decremento de stock genera la alerta ``stock_bajo`` y su mensaje.
El gating por rubro (módulo INVENTARIO) lo decide el caller (comanda_svc).
"""

from __future__ import annotations

ALERTA_STOCK_BAJO = "stock_bajo"


def cruza_stock_minimo(stock_antes: int, stock_despues: int, stock_minimo: int) -> bool:
    """True si el decremento CRUZA el umbral (antes > mínimo >= después).

    Solo el cruce alerta (no cada venta ya bajo el umbral); al reponer stock por
    encima del mínimo, un cruce futuro vuelve a alertar. Con mínimo 0 (default)
    alerta únicamente al agotarse.
    """
    return stock_antes > stock_minimo >= stock_despues


def mensaje_stock_bajo(
    nombre: str, stock: int, stock_minimo: int, *, item_label: str = "Artículo"
) -> str:
    """Mensaje humano para la SmartAlert de stock bajo, en vocabulario del rubro."""
    if stock <= 0:
        return f"{item_label} sin stock: {nombre} (quedan 0)."
    return f"Stock bajo: {nombre} — quedan {stock} (mínimo {stock_minimo})."
