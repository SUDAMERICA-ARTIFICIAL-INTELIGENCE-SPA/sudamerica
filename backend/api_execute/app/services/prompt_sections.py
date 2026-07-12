"""Secciones PURAS del system prompt del orquestador IA (pipeline de eval agéntico, E0).

Módulo puro (mismo patrón que ``rubro_prompt.py``): sin ORM/DB/httpx. Contiene las
constantes de reglas y los formatters/composición del system prompt, movidos VERBATIM
desde ``ai_orchestrator.py``, que ahora delega aquí. El harness offline de
``MVP/backend/evals`` importa este módulo para construir el prompt EXACTO de prod
sin base de datos. Cualquier cambio aquí altera el prompt que ve el LLM: correr
``evals/eval_gate.sh`` antes de tocar.
"""

from __future__ import annotations

from app.services.precio_medida import sufijo_unidad
from app.services.rubro_prompt import build_glosario
from shared.rubros import RUBRO_DEFAULT, Capacidad, Primitiva

# Fase B (Paso 5): rubro_def desde el registro DB-backed (fallback puro a diccionario.py).
from app.services.rubro_registry import rubro_def

COTIZADOR_RULES = """
Reglas para pedidos:
- SOLO usa los precios del catálogo proporcionado. NUNCA inventes precios.
- Si un producto no aparece en el catálogo, di que no está disponible.
- Muestra los productos disponibles relevantes a lo que pide el cliente.
- Incluye precios exactos del catálogo y sugiere combos o acompañamientos cuando tenga sentido.
- Entiende modificadores: "sin cebolla", "extra queso", "tamaño XL" son modificadores de platos.
- Cuando un producto tiene modificadores disponibles, muéstralos al cliente.
- Calcula el total del pedido INCLUYENDO el precio extra de los modificadores.
- Si el cliente pide algo que no está en el menú, indícalo amablemente y sugiere alternativas.
- Pregunta el tipo de entrega usando una encuesta interactiva:
  [ENVIAR_POLL:¿Cómo prefieres recibir tu pedido?|Delivery|Retiro en local|Comer aquí]
- Si es contexto de mesa (el cliente escaneó QR), SALTA esta pregunta — el tipo es automáticamente MESA.
- Acepta respuestas por texto ("delivery", "retiro", etc.) si el cliente no usa la encuesta.
- Al final del pedido, presenta un resumen con items, modificadores, cantidades y total.

Sugerencia de Bebidas y Upselling (OBLIGATORIO):
- ANTES de confirmar el pedido, revisa si el cliente ya pidió alguna bebida.
- DETECTAR BEBIDAS: Productos de categorías como "Bebestibles", "Bebidas", "Jugos",
  "Cervezas", "Vinos", "Tragos", "Refrescos" o similares cuentan como bebidas.
- Si el cliente NO tiene ninguna bebida en su pedido:
  Pregunta: "¿Te gustaría agregar algo para tomar?" y sugiere las bebidas más populares.
  Si hay pocas opciones de bebidas (4 o menos), usa un poll interactivo:
  [ENVIAR_POLL:¿Algo para tomar?|No gracias|{nombre bebida 1}|{nombre bebida 2}]
- Si el cliente YA tiene bebida: sugiere postre o acompañamiento.
- Si pidió solo bebida → sugiere algo para acompañar.
- Si ya tiene plato + bebida → sugiere postre o combo.
- Solo sugiere UNA VEZ. Si el cliente dice que no, respeta su decisión y confirma el pedido.

Disponibilidad:
- Los productos marcados con [NO DISPONIBLE] NO se pueden pedir.
- Si el cliente pide un producto no disponible, infórmale amablemente.

Cuando el cliente CONFIRMA su pedido, responde con el resumen final e incluye al final
un bloque JSON (entre marcadores ```json y ```) con la estructura:
{
  "pedido_confirmado": true,
  "tipo_entrega": "MESA|DELIVERY|RETIRO",
  "numero_mesa": null,
  "direccion_entrega": "direccion completa o null",
  "ubicacion_lat": null,
  "ubicacion_lng": null,
  "metodo_pago": "TRANSFERENCIA|CONTRA_ENTREGA|EFECTIVO|TARJETA",
  "pago_confirmado": false,
  "items": [
    {
      "producto_id": "uuid-del-producto",
      "cantidad": 1,
      "modifiers_json": [{"modifier_id": "uuid-del-modifier"}],
      "notas": "nota especial o null"
    }
  ]
}
Solo incluye el JSON cuando el cliente confirme explícitamente. Si aún está eligiendo, NO incluyas JSON.
""".strip()


# ── Delivery rules ────────────────────────────────────────────────────

DELIVERY_RULES = """
FLUJO DE DELIVERY (cuando el cliente pide delivery):
1. DIRECCION: Pregunta la direccion de entrega. Si el cliente comparte su ubicacion por WhatsApp, acéptala.
   Si no la comparte, vuelve a pedirla. NO confirmes el pedido sin direccion.
2. COSTO: Informa el costo de delivery ANTES de confirmar. Ejemplo: "El costo de envio es $X."
3. PAGO: Pregunta el metodo de pago con encuesta:
   [ENVIAR_POLL:¿Como prefieres pagar?|Transferencia|Efectivo (pago al recibir)|Tarjeta (pago al recibir)]
   - Si elige TRANSFERENCIA: pide confirmacion o comprobante. Si no confirma, NO cierres el pedido.
   - Si elige EFECTIVO: registra metodo_pago="EFECTIVO" y pago_confirmado=false. Continua.
   - Si elige TARJETA: registra metodo_pago="TARJETA" y pago_confirmado=false. Informa que se cobra al momento de la entrega.
4. RESUMEN: Antes de confirmar, muestra resumen completo:
   - Productos y cantidades con precios
   - Subtotal de productos
   - Costo de delivery
   - TOTAL (productos + delivery)
   - Direccion de entrega
   - Metodo de pago
5. CONFIRMACION: Solo cuando el cliente diga "si", "confirmo", "listo" → incluye el JSON con pedido_confirmado=true.
   En el JSON incluye: direccion_entrega, metodo_pago, pago_confirmado (true solo si transferencia fue verificada).
""".strip()


# ── Welcome rules for WhatsApp conversations ─────────────────────────

WELCOME_RULES_WHATSAPP = """
BIENVENIDA (primera interaccion del cliente):
- Cuando un cliente te escribe por primera vez (sin contexto de mesa), dale la bienvenida
  y SIEMPRE ofrece opciones con una encuesta interactiva.
- Usa una encuesta con las opciones principales:
  [ENVIAR_POLL:¿En qué te puedo ayudar?|Hacer un pedido|Ver el menú|Reservar mesa|Delivery|Consultar estado]
- NO hagas preguntas abiertas como primer mensaje. Usa la encuesta para guiar al cliente.
- Si el cliente responde con texto libre en vez de la encuesta, entiende su intencion y continua.
""".strip()

WELCOME_RULES_MESA = """
BIENVENIDA DE MESA (cliente escaneo QR en el local):
- El cliente ya esta sentado en su mesa. Dale la bienvenida de forma calida y ofrece opciones:
  [ENVIAR_POLL:¡Bienvenido! ¿Qué necesitas?|Ver el menú y pedir|Llamar al mesero|Pedir la cuenta]
- Si el cliente elige "Llamar al mesero", responde: "¡Listo! Un mesero se acercará a tu mesa en un momento." y agrega al final: [ALERTA_MESERO]
- Si el cliente elige "Pedir la cuenta", responde solicitando el metodo de pago y agrega al final: [PEDIR_CUENTA]
- Si elige "Ver el menu y pedir", muestra el catalogo y actua como mesero virtual.
""".strip()


def welcome_rules_whatsapp(rubro_key: str) -> str:
    """WELCOME_RULES_WHATSAPP gateado por rubro.

    Restaurante (default) devuelve la constante EXACTA (byte-idéntico). Otros rubros
    reciben una bienvenida compuesta con los labels de sus primitivas y con las opciones
    del poll gateadas por capacidad (reserva solo con AGENDA, delivery solo con DELIVERY)
    — así una peluquería no ofrece "Reservar mesa" ni "Delivery" a su cliente. Fuga §3.A:
    poll de restaurante inyectado a TODO WhatsApp sin gate.
    """
    if rubro_key == RUBRO_DEFAULT:
        return WELCOME_RULES_WHATSAPP
    r = rubro_def(rubro_key)
    lb = r.labels
    opciones = ["Hacer un pedido", f"Ver {lb[Primitiva.CATALOGO]}"]
    if r.tiene_capacidad(Capacidad.AGENDA):
        opciones.append(f"Reservar {lb[Primitiva.AGENDA]}")
    if r.tiene_capacidad(Capacidad.DELIVERY):
        opciones.append("Delivery")
    opciones.append("Consultar estado")
    poll = "|".join(opciones)
    return (
        "BIENVENIDA (primera interaccion del cliente):\n"
        "- Cuando un cliente te escribe por primera vez (sin contexto de recurso), dale la\n"
        "  bienvenida y SIEMPRE ofrece opciones con una encuesta interactiva.\n"
        "- Usa una encuesta con las opciones principales:\n"
        f"  [ENVIAR_POLL:¿En qué te puedo ayudar?|{poll}]\n"
        "- NO hagas preguntas abiertas como primer mensaje. Usa la encuesta para guiar al cliente.\n"
        "- Si el cliente responde con texto libre en vez de la encuesta, entiende su intencion y continua."
    )


def welcome_rules_mesa(rubro_key: str) -> str:
    """WELCOME_RULES_MESA gateado por rubro.

    Restaurante (default) devuelve la constante EXACTA (byte-idéntico). Un rubro con
    recurso físico ≠ restaurante (que expone QR en una silla/box) recibe una bienvenida
    neutral por el label del recurso, sin "mesero"/"Pedir la cuenta"/"buen provecho". Se
    conserva el marcador [ALERTA_MESERO] (lo consume el post-proceso para avisar al equipo).
    """
    if rubro_key == RUBRO_DEFAULT:
        return WELCOME_RULES_MESA
    r = rubro_def(rubro_key)
    recurso = r.labels[Primitiva.RECURSO]
    catalogo = r.labels[Primitiva.CATALOGO]
    return (
        f"BIENVENIDA DE {recurso.upper()} (cliente escaneo QR en el local):\n"
        f"- El cliente ya esta en su {recurso.lower()}. Dale la bienvenida de forma calida y ofrece opciones:\n"
        f"  [ENVIAR_POLL:¡Bienvenido! ¿Qué necesitas?|Ver {catalogo} y pedir|Llamar a un encargado]\n"
        '- Si el cliente elige "Llamar a un encargado", responde: "¡Listo! Un miembro del equipo se acercará '
        'en un momento." y agrega al final: [ALERTA_MESERO]\n'
        f'- Si elige "Ver {catalogo} y pedir", muestra el catalogo y ayudalo con su pedido.'
    )


# ── Stop/restart flow control ────────────────────────────────────────

FLOW_CONTROL_RULES = """
CONTROL DE FLUJO (palabras clave del usuario):
- Si el cliente escribe "parar", "detener", "cancelar", "stop", "para" o similar:
  Responde amablemente: "¡Entendido! He pausado la conversación. Cuando quieras retomar, solo escríbeme."
  NO envíes más mensajes ni sugerencias hasta que el cliente vuelva a escribir.
  NO incluyas JSON de pedido ni marcadores interactivos.
- Si el cliente escribe "reiniciar", "volver", "empezar de nuevo", "nuevo pedido", "reset" o similar:
  Responde: "¡Perfecto! Empecemos de nuevo." y ofrece las opciones iniciales con la lista interactiva.
  Olvida el pedido en curso (NO incluyas JSON del pedido anterior).
""".strip()


# ── Media capability rules (injected when tenant has media assets) ──

MEDIA_RULES_MENU = """
CAPACIDAD DE ENVÍO DE ARCHIVOS:
- Puedes enviar el menú/carta del restaurante en formato PDF.
- Cuando el cliente pida el menú, la carta, los precios en PDF, o cualquier variante,
  responde de forma natural confirmando que se lo envías. El sistema se encarga de adjuntar el archivo automáticamente.
  Ejemplo: "¡Claro! Te envío nuestra carta ahora mismo."
- NUNCA digas que no puedes enviar archivos, PDFs o imágenes. SÍ puedes.
- NO uses marcadores especiales ni corchetes. Solo responde naturalmente.
""".strip()

MEDIA_RULES_IMAGES = """
ENVÍO DE FOTOS DE PLATOS (OBLIGATORIO):
- Los productos del catálogo marcados con [FOTO] tienen imagen disponible.
- Cuando el cliente pregunte por un plato específico o pida ver una foto:
  1. Responde de forma BREVE y natural (1-2 líneas), invitando a ver la imagen
  2. Agrega al FINAL de la respuesta: [ENVIAR_IMAGEN:nombre_exacto_del_producto]
  3. El sistema adjuntará la imagen con el nombre, precio y descripción como caption
  4. NO repitas el precio ni la descripción en el texto — la imagen ya los trae

EJEMPLO CORRECTO:
  Cliente: "¿Cómo es el Churrasco Italiano?"
  Tú: "¡Te muestro cómo se ve nuestro Churrasco Italiano! 😋
       [ENVIAR_IMAGEN:Churrasco Italiano]"

EJEMPLO INCORRECTO (no repitas info que va en el caption):
  "El Churrasco Italiano es $8.900, trae posta, tomate, palta y mayo.
   [ENVIAR_IMAGEN:Churrasco Italiano]"

REGLAS:
- Usa el NOMBRE EXACTO del producto como aparece en el catálogo con [FOTO]
- Solo envía UNA imagen por respuesta
- Si el cliente pregunta genéricamente (ej: "¿qué churrascos tienen?"), muestra la lista
  de opciones en texto y NO uses el marcador (demasiadas imágenes abrumarían)
- Si el producto NO tiene [FOTO] en el catálogo, solo responde con texto (no inventes imagen)
""".strip()

INTERACTIVE_MESSAGE_RULES = """
MENSAJES INTERACTIVOS (WhatsApp):
Puedes enviar encuestas interactivas para que el cliente elija opciones facilmente.

ENCUESTAS (Polls):
- Cuando necesites que el cliente elija entre opciones claras, usa el marcador:
  [ENVIAR_POLL:¿Pregunta?|Opción 1|Opción 2|Opción 3]
- Máximo 12 opciones. Mínimo 2.
- Usa polls para: sucursales, tipo de entrega, método de pago, preferencias, etc.

IMPORTANTE:
- Incluye el marcador AL FINAL de tu respuesta de texto, no al inicio.
- Solo usa UN marcador por respuesta.
- No repitas las opciones en el texto — el marcador genera la encuesta automáticamente.
- NO uses marcadores [ENVIAR_LISTA:...] — solo usa [ENVIAR_POLL:...].
""".strip()


WHATSAPP_FORMAT_RULES = """
FORMATO DE RESPUESTA (WhatsApp):
- Usas WhatsApp. Formatea con sintaxis WhatsApp, NO Markdown.
- Negrita: *texto* (un solo asterisco). NUNCA uses **doble asterisco**.
- Cursiva: _texto_ (guion bajo).
- Tachado: ~texto~.
- Monoespaciado: ```texto```.
- NO uses encabezados (#, ##). Para títulos usa *negrita*.
- NO uses enlaces Markdown [texto](url). Pega la URL directamente.
- Usa listas con guion: - item. O listas numeradas: 1. item.
- Mantén respuestas cortas (máximo 3-4 párrafos). Usa saltos de línea para separar ideas.
- Usa emojis con moderación para dar calidez y estructura visual.
""".strip()

RESERVA_RULES = """
Reglas para reservas de mesa:
- Cuando el cliente quiera reservar mesa, SIEMPRE solicita estos datos en orden:
  1. Fecha y hora deseada
  2. Cantidad de personas
  3. Nombre completo
  4. RUT (obligatorio)
  5. Correo electrónico
- NO confirmes la reserva hasta tener TODOS los datos.
- Si no hay mesas disponibles para el horario solicitado, sugiere alternativas.
- Al confirmar, presenta un resumen claro con todos los datos.
- Sé amigable como un buen anfitrión.

Cuando el cliente confirme TODOS los datos, incluye al final un bloque JSON:
```json
{
  "reserva_confirmada": true,
  "fecha": "YYYY-MM-DD",
  "hora": "HH:MM",
  "cantidad_personas": N,
  "nombre_cliente": "Nombre",
  "rut": "12.345.678-9",
  "email": "email@ejemplo.com"
}
```
Solo incluye el JSON cuando tenga TODOS los datos confirmados.
""".strip()


def _reserva_rules(rubro_key: str) -> str:
    """RESERVA_RULES gateado por rubro.

    Restaurante (default) devuelve la constante EXACTA (byte-idéntico). Un rubro no
    gastronómico con AGENDA (peluquería, veterinaria, spa…) recibe una variante sin el
    vocabulario de "reservar mesa" y con RUT no-obligatorio. El bloque JSON de
    confirmación queda IDÉNTICO para no romper el parser aguas abajo. Fuga detectada
    por el eval (RESERVA_RULES de mesa+RUT inyectada a todo rubro con AGENDA).
    """
    if rubro_key == RUBRO_DEFAULT:
        return RESERVA_RULES
    r = RESERVA_RULES
    r = r.replace("Reglas para reservas de mesa:", "Reglas para reservas y citas:")
    r = r.replace(
        "Cuando el cliente quiera reservar mesa,",
        "Cuando el cliente quiera reservar o agendar,",
    )
    r = r.replace(
        "Si no hay mesas disponibles para el horario solicitado,",
        "Si no hay disponibilidad para el horario solicitado,",
    )
    r = r.replace("4. RUT (obligatorio)", "4. RUT (si lo tiene)")
    r = r.replace("Sé amigable como un buen anfitrión.", "Sé amable y profesional.")
    return r


def _format_product_line(
    product: dict,
    modifier_map: dict[str, list[dict]],
    missing_ingredients: dict[str, list[str]] | None = None,
) -> str:
    """Format a single product (with its modifiers) for LLM consumption."""
    pid = str(product["id"])
    missing = (missing_ingredients or {}).get(pid, [])
    if missing:
        prefix = f"[NO DISPONIBLE - sin {', '.join(missing)}] "
    elif not product.get("disponible", True):
        prefix = "[NO DISPONIBLE] "
    else:
        prefix = ""
    foto_tag = " [FOTO]" if product.get("imagen_url") else ""
    # Módulo precio_medida (F7 M4): "/kg" etc. solo si unidad_venta ≠ 'unidad'.
    unidad_tag = sufijo_unidad(product.get("unidad_venta"))
    line = f"- {prefix}{product['nombre']}: ${product['precio']}{unidad_tag}{foto_tag}"
    if product["descripcion"]:
        line += f" — {product['descripcion']}"
    line += f" (ID: {product['id']})"

    pid = str(product["id"])
    if pid in modifier_map:
        line += _format_modifier_groups(modifier_map[pid])
    return line


def _format_modifier_groups(mods: list[dict]) -> str:
    """Format modifier groups for a product into display lines."""
    groups: dict[str, dict] = {}
    for mod in mods:
        gid = str(mod["group_id"])
        if gid not in groups:
            tipo = "elegir 1" if mod["tipo"] == "SINGLE_SELECT" else "elegir varios"
            oblig = " [OBLIGATORIO]" if mod["obligatorio"] else ""
            groups[gid] = {"header": f"  * {mod['group_nombre']} ({tipo}){oblig}:", "mods": []}
        delta = mod["precio_delta"] or 0
        price_str = f"+${delta}" if delta > 0 else f"-${abs(delta)}" if delta < 0 else "$0"
        groups[gid]["mods"].append(f"    - {mod['mod_nombre']}: {price_str} (ID: {mod['mod_id']})")

    parts: list[str] = []
    for g in groups.values():
        parts.append("\n" + g["header"] + "\n" + "\n".join(g["mods"]))
    return "".join(parts)


def _append_prompt_section(system_prompt: str, section: str) -> str:
    """Append a non-empty section preserving the existing double-line separation."""
    if not section:
        return system_prompt
    return f"{system_prompt}\n\n{section}"


def _remove_span(text: str, start: str, end: str) -> str:
    """Quita ``text[start:end)`` conservando el marcador ``end``. No-op si falta alguno."""
    i = text.find(start)
    if i == -1:
        return text
    j = text.find(end, i)
    if j == -1:
        return text
    return text[:i] + text[j:]


def _cotizador_rules(rubro, rubro_key: str) -> str:
    """COTIZADOR_RULES gateado por rubro.

    Restaurante (default) devuelve la constante EXACTA (byte-idéntico). Un rubro sin
    ``COMANDAS_KDS`` (no gastronómico) omite la opción dine-in "Comer aquí" del poll de
    entrega y el bloque OBLIGATORIO de "Sugerencia de Bebidas y Upselling" — fugas
    detectadas por el eval E4 en ferretería.
    """
    if rubro_key == RUBRO_DEFAULT:
        return COTIZADOR_RULES
    rules = COTIZADOR_RULES
    if not rubro.tiene_capacidad(Capacidad.MESAS):
        rules = rules.replace("|Comer aquí]", "]")
        rules = _remove_span(
            rules,
            "\n\nSugerencia de Bebidas y Upselling (OBLIGATORIO):",
            "\n\nDisponibilidad:",
        )
    return rules


def _build_catalog_section(config: dict | None, catalog: str, rubro, rubro_key: str) -> str:
    """Assemble cotizador rules plus optional availability instructions."""
    if not catalog:
        return ""

    instrucciones = (config or {}).get("instrucciones_disponibilidad") or ""
    section = _cotizador_rules(rubro, rubro_key)
    if instrucciones:
        section += f"\n\nInstrucciones de disponibilidad:\n{instrucciones}"
    return f"{section}\n\n{catalog}"


def _media_rules_menu(rubro_key: str) -> str:
    """MEDIA_RULES_MENU gateado: restaurante byte-idéntico; no gastronómico usa
    "catálogo/carta del negocio" en vez de "menú/carta del restaurante"."""
    if rubro_key == RUBRO_DEFAULT:
        return MEDIA_RULES_MENU
    m = MEDIA_RULES_MENU
    m = m.replace("el menú/carta del restaurante", "el catálogo/carta del negocio")
    m = m.replace(
        "Cuando el cliente pida el menú, la carta,",
        "Cuando el cliente pida el catálogo, la carta,",
    )
    return m


def _media_rules_images(rubro_key: str) -> str:
    """MEDIA_RULES_IMAGES gateado: restaurante byte-idéntico; no gastronómico usa
    "FOTOS DE PRODUCTOS" / "un producto específico" en vez de "PLATOS"/"un plato"."""
    if rubro_key == RUBRO_DEFAULT:
        return MEDIA_RULES_IMAGES
    m = MEDIA_RULES_IMAGES
    m = m.replace("ENVÍO DE FOTOS DE PLATOS (OBLIGATORIO):", "ENVÍO DE FOTOS DE PRODUCTOS (OBLIGATORIO):")
    m = m.replace(
        "Cuando el cliente pregunte por un plato específico",
        "Cuando el cliente pregunte por un producto específico",
    )
    return m


def _build_media_rules_section(catalog: str, has_images: bool, rubro_key: str) -> str:
    """Assemble the media capability rules triggered by catalog/images availability."""
    sections: list[str] = []
    if catalog:
        sections.append(_media_rules_menu(rubro_key))
    if has_images:
        sections.append(_media_rules_images(rubro_key))
    # Always include interactive message rules (polls/lists) for WhatsApp
    sections.append(INTERACTIVE_MESSAGE_RULES)
    return "\n\n".join(sections)


def _format_customer_lines(row, rubro_key: str = RUBRO_DEFAULT) -> list[str]:
    """Format customer context fields into prompt lines.

    Restaurante (default) usa "Plato favorito"/"sugiere su plato favorito" (byte-idéntico);
    otros rubros usan el label genérico "Producto favorito" (R4).
    """
    favorito_label = "Plato favorito" if rubro_key == RUBRO_DEFAULT else "Producto favorito"
    field_map = [
        ("nombre", "Nombre"),
        ("total_pedidos", "Pedidos anteriores"),
        ("total_gastado", "Total gastado"),
        ("plato_favorito", favorito_label),
        ("ultima_visita", "Ultima visita"),
    ]
    lines = ["CONTEXTO DEL CLIENTE (usa esta info para personalizar tu respuesta):"]
    for key, label in field_map:
        val = row.get(key)
        if val:
            prefix = "$" if key == "total_gastado" else ""
            lines.append(f"- {label}: {prefix}{val}")
    estado = row.get("estado_cliente")
    if estado and estado != "NUEVO":
        lines.append(f"- Tipo: {estado}")
    if estado in ("VIP", "FRECUENTE"):
        favorito = "plato favorito" if rubro_key == RUBRO_DEFAULT else "producto favorito"
        lines.append(f"Reconoce al cliente por nombre, agradece su preferencia y sugiere su {favorito}.")
    return lines


def build_catalog_text(
    products: list[dict],
    modifier_map: dict[str, list[dict]],
    missing_ingredients: dict[str, list[str]] | None = None,
) -> tuple[str, bool]:
    """Parte pura de ``_load_product_catalog_with_images``: dicts → texto de catálogo."""
    if not products:
        return "", False
    lines = [_format_product_line(p, modifier_map, missing_ingredients) for p in products]
    has_images = any(p.get("imagen_url") for p in products)
    return "Catálogo de productos:\n" + "\n".join(lines), has_images


def compose_system_prompt(
    base_prompt: str,
    *,
    rubro_key: str,
    knowledge: str = "",
    catalog: str = "",
    has_images: bool = False,
    config: dict | None = None,
    has_mesas: bool = False,
    delivery_config: str = "",
    customer_context: str = "",
) -> str:
    """Composición EXACTA de ``build_system_message`` a partir de datos ya cargados.

    ``ai_orchestrator.build_system_message`` carga de DB y delega aquí; el harness
    de evals carga de fixtures y delega aquí. Misma función = mismo prompt.
    """
    system_prompt = base_prompt
    rubro = rubro_def(rubro_key)
    if rubro_key != RUBRO_DEFAULT:
        system_prompt = _append_prompt_section(system_prompt, build_glosario(rubro_key))
    system_prompt = _append_prompt_section(system_prompt, knowledge)
    system_prompt = _append_prompt_section(system_prompt, _build_catalog_section(config, catalog, rubro, rubro_key))
    system_prompt = _append_prompt_section(system_prompt, _build_media_rules_section(catalog, has_images, rubro_key))
    if rubro.tiene_capacidad(Capacidad.AGENDA) and has_mesas:
        system_prompt = _append_prompt_section(system_prompt, _reserva_rules(rubro_key))
    if rubro.tiene_capacidad(Capacidad.DELIVERY):
        system_prompt = _append_prompt_section(system_prompt, DELIVERY_RULES)
        system_prompt = _append_prompt_section(system_prompt, delivery_config)
    system_prompt = _append_prompt_section(system_prompt, FLOW_CONTROL_RULES)
    system_prompt = _append_prompt_section(system_prompt, customer_context)
    return system_prompt
