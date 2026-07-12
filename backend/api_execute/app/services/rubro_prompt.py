"""Construcción de secciones de prompt dependientes del rubro (F1 multi-rubro).

Módulo PURO: importa solo ``shared.rubros`` (sin ORM/DB) para ser testeable aislado.
Genera el bloque "GLOSARIO DEL NEGOCIO" que reencuadra el vocabulario del asistente
según el rubro del tenant. El caller (ai_orchestrator / prompts_ai) decide cuándo
inyectarlo; por convención NO se inyecta para el rubro por defecto (restaurante), que
ya está escrito en ese vocabulario.
"""

from __future__ import annotations

from shared.rubros import Capacidad, Primitiva

# Fase B (Paso 5): rubro_def desde el registro DB-backed (fallback puro a diccionario.py).
from app.services.rubro_registry import rubro_def


def build_glosario(rubro_key: str) -> str:
    """Bloque compacto que le dice al LLM cómo nombrar cada primitiva en ESTE rubro."""
    r = rubro_def(rubro_key)
    lb = r.labels
    lines = [
        f"GLOSARIO DEL NEGOCIO — este negocio es: {r.nombre} {r.emoji}.".rstrip(),
        "Usa SIEMPRE este vocabulario al comunicarte con el cliente; NO uses términos de otros rubros:",
        f'- El catálogo se llama "{lb[Primitiva.CATALOGO]}"; cada ítem es un "{lb[Primitiva.ITEM]}"; '
        f'se agrupan en "{lb[Primitiva.CATEGORIA]}".',
        f'- Quien compra es un "{lb[Primitiva.PARTE]}"; una venta es una "{lb[Primitiva.TRANSACCION]}".',
    ]
    if r.tiene_capacidad(Capacidad.AGENDA):
        lines.append(f'- Las reservas de tiempo se llaman "{lb[Primitiva.AGENDA]}".')
    if r.recurso:
        lines.append(f'- El recurso reservable es "{lb[Primitiva.RECURSO]}".')
    if r.variantes:
        lines.append(f'- Las opciones configurables se llaman "{lb[Primitiva.VARIANTE]}".')
    if r.tiene_capacidad(Capacidad.INVENTARIO):
        lines.append(
            f'- El negocio controla stock por "{lb[Primitiva.ITEM].lower()}": si un ítem aparece '
            "[NO DISPONIBLE] está sin stock; no lo ofrezcas y sugiere una alternativa del catálogo."
        )
    if r.sub_entidad_label:
        lines.append(
            f'- Cada cliente puede tener una o más "{r.sub_entidad_label}" asociadas: '
            f"pregunta y registra por cuál {r.sub_entidad_label.lower()} consulta."
        )
    if r.precio_medida:
        lines.append(
            "- Hay ítems con precio por medida/peso: indica SIEMPRE la unidad (kg, m², hora) al cotizar."
        )
    if not r.tiene_capacidad(Capacidad.DELIVERY):
        lines.append("- Este negocio NO hace delivery: no ofrezcas envío a domicilio.")
    if not r.tiene_capacidad(Capacidad.MESAS):
        lines.append("- No hables de cocina, comandas ni preparación de platos.")
    return "\n".join(lines)


def incluye_capacidad(rubro_key: str, capacidad: str) -> bool:
    """Azúcar sobre ``rubro_def(...).tiene_capacidad`` para el gating de secciones."""
    return rubro_def(rubro_key).tiene_capacidad(capacidad)


def extract_prompt_generico(rubro_key: str) -> str:
    """Prompt de extracción de catálogo generalizado (rubros no-gastronómicos).

    Reencuadra el prompt de importación usando el vocabulario del rubro (catálogo/
    ítem/categoría) en vez del vocabulario de restaurante. Conserva las reglas de
    extracción (secciones reales, precio entero, un ítem por variante) que son las
    que realmente gobiernan la calidad, independientes del rubro.
    """
    r = rubro_def(rubro_key)
    lb = r.labels
    item = lb[Primitiva.ITEM].lower()
    catalogo = lb[Primitiva.CATALOGO].lower()
    categoria = lb[Primitiva.CATEGORIA].lower()
    return (
        f"Eres un sistema experto de extraccion de {catalogo} para un negocio del tipo: {r.nombre}.\n"
        f"Analiza el archivo adjunto y extrae TODOS los items (cada uno es un {item}), "
        "organizados correctamente.\n\n"
        "Responde SOLO con JSON valido, sin texto adicional:\n"
        "{\n"
        '  "items": [\n'
        "    {\n"
        f'      "nombre": "Nombre del {item} (incluye variante/medida si aplica)",\n'
        '      "descripcion": "Detalle breve, o null",\n'
        '      "precio": 5990,\n'
        f'      "categoria": "Seccion ({categoria}) exacta donde aparece"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "REGLAS CRITICAS DE ORGANIZACION:\n"
        f"- **categoria** debe ser la seccion/titulo/encabezado REAL del documento tal como aparece "
        f"(el equivalente a un(a) {categoria}). No inventes nombres genericos.\n"
        "- Si hay sub-secciones visibles, usalas como categoria.\n"
        "- Si un item aparece con multiples variantes/medidas/precios (ej: Chico $85, Grande $180), "
        'crea UN item por cada variante con el formato "NOMBRE - Variante".\n'
        '- NUNCA uses "General" si puedes inferir una categoria razonable del contexto.\n\n'
        "REGLAS DE DATOS:\n"
        "- Precio SIEMPRE en numero entero (sin puntos ni comas de miles, sin simbolo $).\n"
        "- Si el precio tiene decimales, redondea al entero mas cercano.\n"
        "- Si no puedes determinar el precio, pon 0.\n"
        "- descripcion: incluye detalle si esta visible, o null si no hay descripcion.\n"
        "- Extrae TODOS los items, no solo algunos. No inventes items que no estan en el documento.\n"
        "- Mantén el orden original en que aparecen."
    )
