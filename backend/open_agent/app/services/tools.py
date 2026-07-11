"""Admin copilot tool definitions and execution.

Each tool calls api_execute endpoints via service JWT to get/modify data.
Sudamérica AI has full CRUD access to all modules EXCEPT:
- Cannot change SUPERADMIN role or deactivate SUPERADMIN users.
"""

import json
import logging
from uuid import UUID

import httpx

from app.config import OpenAgentSettings
from shared.middleware import build_service_auth_headers

logger = logging.getLogger(__name__)


# ── Tool definitions (OpenAI function-calling format) ────────────────

TOOL_DEFINITIONS: list[dict] = [
    # ── Ventas ──
    {
        "type": "function",
        "function": {
            "name": "consultar_ventas",
            "description": (
                "Consulta las ventas/pedidos del restaurante. "
                "Retorna lista de ventas con producto, cantidad, total y fecha."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page_size": {
                        "type": "integer",
                        "description": "Cantidad de ventas a consultar (default 20, max 100)",
                    },
                },
                "required": [],
            },
        },
    },
    # ── Productos ──
    {
        "type": "function",
        "function": {
            "name": "consultar_productos",
            "description": (
                "Consulta el menu/carta completa del restaurante. "
                "Retorna productos con nombre, precio, disponibilidad y categoria."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modificar_producto",
            "description": (
                "Modifica un producto del menu. Puede cambiar precio, "
                "disponibilidad, nombre o descripcion."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "producto_id": {
                        "type": "string",
                        "description": "UUID del producto a modificar",
                    },
                    "precio": {"type": "number", "description": "Nuevo precio"},
                    "disponible": {"type": "boolean", "description": "Disponibilidad (true/false)"},
                    "nombre": {"type": "string", "description": "Nuevo nombre"},
                    "descripcion": {"type": "string", "description": "Nueva descripcion"},
                },
                "required": ["producto_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "eliminar_producto",
            "description": "Elimina (desactiva) un producto del menu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "producto_id": {"type": "string", "description": "UUID del producto a eliminar"},
                },
                "required": ["producto_id"],
            },
        },
    },
    # ── Categorias ──
    {
        "type": "function",
        "function": {
            "name": "crear_categoria",
            "description": (
                "Crea una nueva seccion/categoria en el menu del restaurante. "
                "Ejemplo: 'Entradas', 'Bebestibles', 'Postres', 'Pizzas', 'Combos'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre de la seccion"},
                    "descripcion": {"type": "string", "description": "Descripcion opcional"},
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_producto",
            "description": (
                "Crea un nuevo producto/plato en el menu del restaurante. "
                "Debe especificar nombre y precio. Opcionalmente categoria, descripcion."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre del producto"},
                    "precio": {"type": "number", "description": "Precio del producto"},
                    "categoria_id": {"type": "string", "description": "UUID de la categoria"},
                    "descripcion": {"type": "string", "description": "Descripcion del producto"},
                    "disponible": {"type": "boolean", "description": "Disponibilidad (default true)"},
                },
                "required": ["nombre", "precio"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_categorias",
            "description": "Consulta las secciones/categorias del menu.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modificar_categoria",
            "description": "Modifica una categoria del menu (nombre o descripcion).",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria_id": {"type": "string", "description": "UUID de la categoria"},
                    "nombre": {"type": "string", "description": "Nuevo nombre"},
                    "descripcion": {"type": "string", "description": "Nueva descripcion"},
                },
                "required": ["categoria_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "eliminar_categoria",
            "description": "Elimina (desactiva) una categoria del menu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria_id": {"type": "string", "description": "UUID de la categoria"},
                },
                "required": ["categoria_id"],
            },
        },
    },
    # ── Leads/Clientes ──
    {
        "type": "function",
        "function": {
            "name": "consultar_clientes",
            "description": (
                "Consulta los clientes/leads del restaurante. "
                "Retorna lista con nombre, estado, canal, total de pedidos y gasto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page_size": {"type": "integer", "description": "Cantidad (default 20)"},
                    "estado": {"type": "string", "description": "Filtrar por estado: NUEVO, CONTACTADO, EN_PROCESO, CONVERTIDO, DESCARTADO"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_cliente",
            "description": "Crea un nuevo cliente/lead en el sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre del cliente"},
                    "telefono": {"type": "string", "description": "Telefono (con codigo pais, ej: 56912345678)"},
                    "email": {"type": "string", "description": "Email opcional"},
                    "canal": {"type": "string", "description": "Canal: WHATSAPP, WEB, TELEFONO, PRESENCIAL"},
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modificar_cliente",
            "description": "Modifica datos de un cliente/lead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "UUID del cliente/lead"},
                    "nombre": {"type": "string", "description": "Nuevo nombre"},
                    "telefono": {"type": "string", "description": "Nuevo telefono"},
                    "email": {"type": "string", "description": "Nuevo email"},
                },
                "required": ["lead_id"],
            },
        },
    },
    # ── Metricas ──
    {
        "type": "function",
        "function": {
            "name": "consultar_metricas",
            "description": (
                "Consulta las metricas principales del restaurante: "
                "ingresos totales, numero de ventas, tasa de conversion, "
                "y distribucion de clientes por estado."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ── Comandas ──
    {
        "type": "function",
        "function": {
            "name": "consultar_comandas",
            "description": (
                "Consulta las comandas/ordenes recientes del restaurante. "
                "Retorna pedidos con estado, tipo de entrega, items y total."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "estado": {
                        "type": "string",
                        "description": "Filtrar por estado",
                        "enum": ["PENDIENTE", "EN_COCINA", "LISTO", "ENTREGADO", "CANCELADO"],
                    },
                    "page_size": {"type": "integer", "description": "Cantidad (default 20)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cambiar_estado_comanda",
            "description": (
                "Cambia el estado de una comanda. Transiciones validas: "
                "PENDIENTE→EN_COCINA→LISTO→ENTREGADO, o CANCELADO desde cualquier estado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "comanda_id": {"type": "string", "description": "UUID de la comanda"},
                    "estado": {
                        "type": "string",
                        "description": "Nuevo estado",
                        "enum": ["PENDIENTE", "EN_COCINA", "LISTO", "ENTREGADO", "CANCELADO"],
                    },
                },
                "required": ["comanda_id", "estado"],
            },
        },
    },
    # ── Mesas ──
    {
        "type": "function",
        "function": {
            "name": "consultar_mesas",
            "description": "Consulta las mesas del restaurante con su numero y capacidad.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_mesa",
            "description": "Crea una nueva mesa en el restaurante.",
            "parameters": {
                "type": "object",
                "properties": {
                    "numero": {"type": "integer", "description": "Numero de mesa"},
                    "capacidad": {"type": "integer", "description": "Capacidad de personas"},
                    "zona": {"type": "string", "description": "Zona (ej: 'terraza', 'salon', 'bar')"},
                },
                "required": ["numero"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modificar_mesa",
            "description": "Modifica una mesa (numero, capacidad, zona).",
            "parameters": {
                "type": "object",
                "properties": {
                    "mesa_id": {"type": "string", "description": "UUID de la mesa"},
                    "numero": {"type": "integer", "description": "Nuevo numero"},
                    "capacidad": {"type": "integer", "description": "Nueva capacidad"},
                    "zona": {"type": "string", "description": "Nueva zona"},
                },
                "required": ["mesa_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "eliminar_mesa",
            "description": "Elimina (desactiva) una mesa del restaurante.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mesa_id": {"type": "string", "description": "UUID de la mesa"},
                },
                "required": ["mesa_id"],
            },
        },
    },
    # ── Modifiers ──
    {
        "type": "function",
        "function": {
            "name": "consultar_modifier_groups",
            "description": "Consulta los grupos de modificadores (ej: 'Tamano', 'Extras', 'Salsas').",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_modifier_group",
            "description": "Crea un grupo de modificadores con sus opciones.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre del grupo (ej: 'Tamano')"},
                    "tipo": {"type": "string", "description": "SINGLE (elige uno) o MULTI (elige varios)", "enum": ["SINGLE", "MULTI"]},
                    "requerido": {"type": "boolean", "description": "Si es obligatorio elegir (default false)"},
                },
                "required": ["nombre"],
            },
        },
    },
    # ── Reservaciones ──
    {
        "type": "function",
        "function": {
            "name": "consultar_reservaciones",
            "description": (
                "Consulta las reservaciones del restaurante. "
                "Retorna lista con fecha, hora, nombre del cliente, personas, mesa y estado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {
                        "type": "string",
                        "description": "Filtrar por fecha (formato YYYY-MM-DD)",
                    },
                    "estado": {
                        "type": "string",
                        "description": "Filtrar por estado",
                        "enum": ["PENDIENTE", "CONFIRMADA", "CANCELADA"],
                    },
                    "page_size": {"type": "integer", "description": "Cantidad (default 20)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_reservacion",
            "description": (
                "Crea una nueva reservacion. Requiere fecha, hora de inicio, "
                "cantidad de personas y nombre del cliente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha_reserva": {"type": "string", "description": "Fecha (YYYY-MM-DD)"},
                    "hora_inicio": {"type": "string", "description": "Hora de inicio (HH:MM)"},
                    "cantidad_personas": {"type": "integer", "description": "Numero de personas"},
                    "nombre_cliente": {"type": "string", "description": "Nombre del cliente"},
                    "telefono": {"type": "string", "description": "Telefono del cliente (opcional)"},
                    "email": {"type": "string", "description": "Email del cliente (opcional)"},
                    "mesa_id": {"type": "string", "description": "UUID de la mesa (opcional, se auto-asigna)"},
                    "notas": {"type": "string", "description": "Notas adicionales"},
                },
                "required": ["fecha_reserva", "hora_inicio", "cantidad_personas", "nombre_cliente"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modificar_reservacion",
            "description": (
                "Modifica una reservacion existente (estado, fecha, hora, personas, notas). "
                "Para confirmar una reservacion, cambiar estado a CONFIRMADA."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reservacion_id": {"type": "string", "description": "UUID de la reservacion"},
                    "estado": {
                        "type": "string",
                        "description": "Nuevo estado",
                        "enum": ["PENDIENTE", "CONFIRMADA", "CANCELADA"],
                    },
                    "fecha_reserva": {"type": "string", "description": "Nueva fecha (YYYY-MM-DD)"},
                    "hora_inicio": {"type": "string", "description": "Nueva hora (HH:MM)"},
                    "cantidad_personas": {"type": "integer", "description": "Nueva cantidad de personas"},
                    "notas": {"type": "string", "description": "Nuevas notas"},
                },
                "required": ["reservacion_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancelar_reservacion",
            "description": "Cancela una reservacion existente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservacion_id": {"type": "string", "description": "UUID de la reservacion"},
                },
                "required": ["reservacion_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_disponibilidad_mesas",
            "description": (
                "Consulta que mesas estan disponibles para una fecha, hora y cantidad de personas. "
                "Util para saber si se puede hacer una reservacion."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "Fecha (YYYY-MM-DD)"},
                    "hora": {"type": "string", "description": "Hora (HH:MM)"},
                    "cantidad_personas": {"type": "integer", "description": "Numero de personas"},
                },
                "required": ["fecha", "hora", "cantidad_personas"],
            },
        },
    },
    # ── Usuarios (equipo) ──
    {
        "type": "function",
        "function": {
            "name": "consultar_equipo",
            "description": (
                "Consulta los usuarios/miembros del equipo del restaurante. "
                "Retorna nombre, email, rol y estado."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modificar_usuario",
            "description": (
                "Modifica datos de un miembro del equipo. "
                "IMPORTANTE: No puede cambiar el rol ni desactivar usuarios SUPERADMIN."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "usuario_id": {"type": "string", "description": "UUID del usuario"},
                    "nombre": {"type": "string", "description": "Nuevo nombre"},
                    "apellido": {"type": "string", "description": "Nuevo apellido"},
                    "email": {"type": "string", "description": "Nuevo email"},
                },
                "required": ["usuario_id"],
            },
        },
    },
]


# ── Tool execution ───────────────────────────────────────────────────

def _build_headers(
    tenant_id: UUID,
    settings: OpenAgentSettings,
    scopes: tuple[str, ...],
) -> dict[str, str]:
    """Build service auth headers for calling api_execute."""
    headers = build_service_auth_headers(
        service_name="open_agent",
        audience="api_execute",
        tenant_id=tenant_id,
        secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        scopes=scopes,
        expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )
    headers["X-Tenant-ID"] = str(tenant_id)
    return headers


async def _api_get(
    path: str, tenant_id: UUID, settings: OpenAgentSettings,
    scopes: tuple[str, ...], http_client: httpx.AsyncClient,
    params: dict | None = None,
) -> dict:
    """GET to api_execute with service auth."""
    url = f"{settings.SERVICE_API_EXECUTE_URL}{path}"
    headers = _build_headers(tenant_id, settings, scopes)
    response = await http_client.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


async def _api_post(
    path: str, body: dict, tenant_id: UUID, settings: OpenAgentSettings,
    scopes: tuple[str, ...], http_client: httpx.AsyncClient,
) -> dict:
    """POST to api_execute with service auth."""
    url = f"{settings.SERVICE_API_EXECUTE_URL}{path}"
    headers = _build_headers(tenant_id, settings, scopes)
    response = await http_client.post(url, json=body, headers=headers)
    response.raise_for_status()
    return response.json()


async def _api_patch(
    path: str, body: dict, tenant_id: UUID, settings: OpenAgentSettings,
    scopes: tuple[str, ...], http_client: httpx.AsyncClient,
) -> dict:
    """PATCH to api_execute with service auth."""
    url = f"{settings.SERVICE_API_EXECUTE_URL}{path}"
    headers = _build_headers(tenant_id, settings, scopes)
    response = await http_client.patch(url, json=body, headers=headers)
    response.raise_for_status()
    return response.json()


async def _api_delete(
    path: str, tenant_id: UUID, settings: OpenAgentSettings,
    scopes: tuple[str, ...], http_client: httpx.AsyncClient,
) -> None:
    """DELETE to api_execute with service auth."""
    url = f"{settings.SERVICE_API_EXECUTE_URL}{path}"
    headers = _build_headers(tenant_id, settings, scopes)
    response = await http_client.delete(url, headers=headers)
    response.raise_for_status()


def _summarize(data: dict | list, max_len: int = 3000) -> str:
    """JSON-serialize, truncating if too long."""
    text = json.dumps(data, ensure_ascii=False, default=str)
    if len(text) > max_len:
        text = text[:max_len] + "... (truncado)"
    return text


def _require_arg(arguments: dict, field: str) -> str:
    """Extract a required argument or return an error JSON string."""
    val = arguments.get(field)
    if not val:
        return ""
    return str(val)


# ── Dispatch table ───────────────────────────────────────────────────

async def execute_tool(
    tool_name: str,
    arguments: dict,
    tenant_id: UUID,
    settings: OpenAgentSettings,
    http_client: httpx.AsyncClient,
) -> str:
    """Execute a tool by name and return the result as a string."""
    try:
        return await _dispatch_tool(tool_name, arguments, tenant_id, settings, http_client)
    except httpx.HTTPStatusError as exc:
        logger.error("Tool %s failed: HTTP %s", tool_name, exc.response.status_code)
        return json.dumps({
            "error": f"Error al ejecutar {tool_name}",
            "status": exc.response.status_code,
            "detail": exc.response.text[:500],
        })
    except Exception as exc:
        logger.error("Tool %s failed: %s", tool_name, exc, exc_info=True)
        return json.dumps({"error": f"Error interno al ejecutar {tool_name}"})


async def _dispatch_tool(
    tool_name: str,
    arguments: dict,
    tenant_id: UUID,
    settings: OpenAgentSettings,
    http_client: httpx.AsyncClient,
) -> str:
    """Route tool_name to the correct handler via dispatch table."""
    handler = _TOOL_HANDLERS.get(tool_name)
    if handler is None:
        return json.dumps({"error": f"Herramienta desconocida: {tool_name}"})
    return await handler(arguments, tenant_id, settings, http_client)


# ── Individual tool handlers ─────────────────────────────────────────

async def _handle_consultar_ventas(arguments, tenant_id, settings, http_client):
    page_size = arguments.get("page_size", 20)
    data = await _api_get(
        "/api/v1/core/ventas", tenant_id, settings,
        ("ventas:read",), http_client,
        params={"page_size": min(page_size, 100)},
    )
    return _summarize(data)


async def _handle_consultar_productos(arguments, tenant_id, settings, http_client):
    data = await _api_get(
        "/api/v1/core/productos", tenant_id, settings,
        ("productos:read",), http_client,
        params={"page_size": 100},
    )
    return _summarize(data)


async def _handle_modificar_producto(arguments, tenant_id, settings, http_client):
    pid = _require_arg(arguments, "producto_id")
    if not pid:
        return '{"error": "producto_id es requerido"}'
    body = {k: arguments[k] for k in ("precio", "disponible", "nombre", "descripcion") if k in arguments}
    if not body:
        return '{"error": "No se especificaron campos a modificar"}'
    data = await _api_patch(
        f"/api/v1/core/productos/{pid}", body,
        tenant_id, settings, ("productos:write",), http_client,
    )
    return _summarize(data)


async def _handle_eliminar_producto(arguments, tenant_id, settings, http_client):
    pid = _require_arg(arguments, "producto_id")
    if not pid:
        return '{"error": "producto_id es requerido"}'
    await _api_delete(
        f"/api/v1/core/productos/{pid}",
        tenant_id, settings, ("productos:write",), http_client,
    )
    return '{"ok": true, "mensaje": "Producto eliminado"}'


async def _handle_crear_producto(arguments, tenant_id, settings, http_client):
    nombre = arguments.get("nombre")
    precio = arguments.get("precio")
    if not nombre or precio is None:
        return '{"error": "nombre y precio son requeridos"}'
    body: dict = {"nombre": nombre, "precio": precio}
    for field in ("categoria_id", "descripcion", "disponible"):
        if field in arguments:
            body[field] = arguments[field]
    data = await _api_post(
        "/api/v1/core/productos", body,
        tenant_id, settings, ("productos:write",), http_client,
    )
    return _summarize(data)


async def _handle_consultar_categorias(arguments, tenant_id, settings, http_client):
    data = await _api_get(
        "/api/v1/core/categorias", tenant_id, settings,
        ("categorias:read",), http_client,
        params={"page_size": 100},
    )
    return _summarize(data)


async def _handle_crear_categoria(arguments, tenant_id, settings, http_client):
    nombre = arguments.get("nombre")
    if not nombre:
        return '{"error": "nombre es requerido"}'
    body = {"nombre": nombre}
    if "descripcion" in arguments:
        body["descripcion"] = arguments["descripcion"]
    data = await _api_post(
        "/api/v1/core/categorias", body,
        tenant_id, settings, ("categorias:write",), http_client,
    )
    return _summarize(data)


async def _handle_modificar_categoria(arguments, tenant_id, settings, http_client):
    cid = _require_arg(arguments, "categoria_id")
    if not cid:
        return '{"error": "categoria_id es requerido"}'
    body = {k: arguments[k] for k in ("nombre", "descripcion") if k in arguments}
    if not body:
        return '{"error": "No se especificaron campos a modificar"}'
    data = await _api_patch(
        f"/api/v1/core/categorias/{cid}", body,
        tenant_id, settings, ("categorias:write",), http_client,
    )
    return _summarize(data)


async def _handle_eliminar_categoria(arguments, tenant_id, settings, http_client):
    cid = _require_arg(arguments, "categoria_id")
    if not cid:
        return '{"error": "categoria_id es requerido"}'
    await _api_delete(
        f"/api/v1/core/categorias/{cid}",
        tenant_id, settings, ("categorias:write",), http_client,
    )
    return '{"ok": true, "mensaje": "Categoria eliminada"}'


async def _handle_consultar_clientes(arguments, tenant_id, settings, http_client):
    page_size = arguments.get("page_size", 20)
    params: dict = {"page_size": min(page_size, 100)}
    if "estado" in arguments:
        params["estado"] = arguments["estado"]
    data = await _api_get(
        "/api/v1/core/leads", tenant_id, settings,
        ("leads:read",), http_client, params=params,
    )
    return _summarize(data)


async def _handle_crear_cliente(arguments, tenant_id, settings, http_client):
    nombre = arguments.get("nombre")
    if not nombre:
        return '{"error": "nombre es requerido"}'
    body = {"nombre": nombre}
    for field in ("telefono", "email", "canal"):
        if field in arguments:
            body[field] = arguments[field]
    data = await _api_post(
        "/api/v1/core/leads", body,
        tenant_id, settings, ("leads:write",), http_client,
    )
    return _summarize(data)


async def _handle_modificar_cliente(arguments, tenant_id, settings, http_client):
    lid = _require_arg(arguments, "lead_id")
    if not lid:
        return '{"error": "lead_id es requerido"}'
    body = {k: arguments[k] for k in ("nombre", "telefono", "email") if k in arguments}
    if not body:
        return '{"error": "No se especificaron campos a modificar"}'
    data = await _api_patch(
        f"/api/v1/core/leads/{lid}", body,
        tenant_id, settings, ("leads:write",), http_client,
    )
    return _summarize(data)


async def _handle_consultar_metricas(arguments, tenant_id, settings, http_client):
    revenue = await _api_get(
        "/api/v1/core/metricas/revenue", tenant_id, settings,
        ("metricas:read",), http_client,
    )
    conversion = await _api_get(
        "/api/v1/core/metricas/conversion", tenant_id, settings,
        ("metricas:read",), http_client,
    )
    leads_estado = await _api_get(
        "/api/v1/core/metricas/leads-estado", tenant_id, settings,
        ("metricas:read",), http_client,
    )
    return _summarize({
        "revenue": revenue,
        "conversion": conversion,
        "leads_por_estado": leads_estado,
    })


async def _handle_consultar_comandas(arguments, tenant_id, settings, http_client):
    params_dict: dict = {"page_size": min(arguments.get("page_size", 20), 100)}
    if "estado" in arguments:
        params_dict["estado"] = arguments["estado"]
    data = await _api_get(
        "/api/v1/core/comandas", tenant_id, settings,
        ("comandas:read",), http_client, params=params_dict,
    )
    return _summarize(data)


async def _handle_cambiar_estado_comanda(arguments, tenant_id, settings, http_client):
    cid = _require_arg(arguments, "comanda_id")
    estado = arguments.get("estado")
    if not cid or not estado:
        return '{"error": "comanda_id y estado son requeridos"}'
    data = await _api_patch(
        f"/api/v1/core/comandas/{cid}/estado",
        {"estado": estado},
        tenant_id, settings, ("comandas:write",), http_client,
    )
    return _summarize(data)


async def _handle_consultar_mesas(arguments, tenant_id, settings, http_client):
    data = await _api_get(
        "/api/v1/core/mesas", tenant_id, settings,
        ("mesas:read",), http_client,
        params={"page_size": 100},
    )
    return _summarize(data)


async def _handle_crear_mesa(arguments, tenant_id, settings, http_client):
    numero = arguments.get("numero")
    if numero is None:
        return '{"error": "numero es requerido"}'
    body = {"numero": numero}
    for field in ("capacidad", "zona"):
        if field in arguments:
            body[field] = arguments[field]
    data = await _api_post(
        "/api/v1/core/mesas", body,
        tenant_id, settings, ("mesas:write",), http_client,
    )
    return _summarize(data)


async def _handle_modificar_mesa(arguments, tenant_id, settings, http_client):
    mid = _require_arg(arguments, "mesa_id")
    if not mid:
        return '{"error": "mesa_id es requerido"}'
    body = {k: arguments[k] for k in ("numero", "capacidad", "zona") if k in arguments}
    if not body:
        return '{"error": "No se especificaron campos a modificar"}'
    data = await _api_patch(
        f"/api/v1/core/mesas/{mid}", body,
        tenant_id, settings, ("mesas:write",), http_client,
    )
    return _summarize(data)


async def _handle_eliminar_mesa(arguments, tenant_id, settings, http_client):
    mid = _require_arg(arguments, "mesa_id")
    if not mid:
        return '{"error": "mesa_id es requerido"}'
    await _api_delete(
        f"/api/v1/core/mesas/{mid}",
        tenant_id, settings, ("mesas:write",), http_client,
    )
    return '{"ok": true, "mensaje": "Mesa eliminada"}'


async def _handle_consultar_modifier_groups(arguments, tenant_id, settings, http_client):
    data = await _api_get(
        "/api/v1/core/modifier-groups", tenant_id, settings,
        ("modifiers:read",), http_client,
        params={"page_size": 100},
    )
    return _summarize(data)


async def _handle_crear_modifier_group(arguments, tenant_id, settings, http_client):
    nombre = arguments.get("nombre")
    if not nombre:
        return '{"error": "nombre es requerido"}'
    body = {"nombre": nombre}
    for field in ("tipo", "requerido"):
        if field in arguments:
            body[field] = arguments[field]
    data = await _api_post(
        "/api/v1/core/modifier-groups", body,
        tenant_id, settings, ("modifiers:write",), http_client,
    )
    return _summarize(data)


async def _handle_consultar_reservaciones(arguments, tenant_id, settings, http_client):
    params_dict: dict = {"page_size": min(arguments.get("page_size", 20), 100)}
    if "fecha" in arguments:
        params_dict["fecha"] = arguments["fecha"]
    if "estado" in arguments:
        params_dict["estado"] = arguments["estado"]
    data = await _api_get(
        "/api/v1/core/reservaciones", tenant_id, settings,
        ("reservaciones:read",), http_client, params=params_dict,
    )
    return _summarize(data)


async def _handle_crear_reservacion(arguments, tenant_id, settings, http_client):
    for field in ("fecha_reserva", "hora_inicio", "cantidad_personas", "nombre_cliente"):
        if field not in arguments:
            return f'{{"error": "{field} es requerido"}}'
    body = {k: arguments[k] for k in (
        "fecha_reserva", "hora_inicio", "cantidad_personas", "nombre_cliente",
        "telefono", "email", "mesa_id", "notas",
    ) if k in arguments}
    data = await _api_post(
        "/api/v1/core/reservaciones", body,
        tenant_id, settings, ("reservaciones:write",), http_client,
    )
    return _summarize(data)


async def _handle_modificar_reservacion(arguments, tenant_id, settings, http_client):
    rid = _require_arg(arguments, "reservacion_id")
    if not rid:
        return '{"error": "reservacion_id es requerido"}'
    body = {k: arguments[k] for k in (
        "estado", "fecha_reserva", "hora_inicio", "cantidad_personas", "notas",
    ) if k in arguments}
    if not body:
        return '{"error": "No se especificaron campos a modificar"}'
    data = await _api_patch(
        f"/api/v1/core/reservaciones/{rid}", body,
        tenant_id, settings, ("reservaciones:write",), http_client,
    )
    return _summarize(data)


async def _handle_cancelar_reservacion(arguments, tenant_id, settings, http_client):
    rid = _require_arg(arguments, "reservacion_id")
    if not rid:
        return '{"error": "reservacion_id es requerido"}'
    await _api_delete(
        f"/api/v1/core/reservaciones/{rid}",
        tenant_id, settings, ("reservaciones:write",), http_client,
    )
    return '{"ok": true, "mensaje": "Reservacion cancelada"}'


async def _handle_consultar_disponibilidad_mesas(arguments, tenant_id, settings, http_client):
    for field in ("fecha", "hora", "cantidad_personas"):
        if field not in arguments:
            return f'{{"error": "{field} es requerido"}}'
    data = await _api_get(
        "/api/v1/core/reservaciones/disponibilidad", tenant_id, settings,
        ("reservaciones:read",), http_client,
        params={
            "fecha": arguments["fecha"],
            "hora": arguments["hora"],
            "cantidad_personas": arguments["cantidad_personas"],
        },
    )
    return _summarize(data)


async def _handle_consultar_equipo(arguments, tenant_id, settings, http_client):
    data = await _api_get(
        "/api/v1/core/usuarios", tenant_id, settings,
        ("usuarios:read",), http_client,
        params={"page_size": 100},
    )
    return _summarize(data)


async def _handle_modificar_usuario(arguments, tenant_id, settings, http_client):
    uid = _require_arg(arguments, "usuario_id")
    if not uid:
        return '{"error": "usuario_id es requerido"}'
    body = {k: arguments[k] for k in ("nombre", "apellido", "email") if k in arguments}
    if not body:
        return '{"error": "No se especificaron campos a modificar"}'
    data = await _api_patch(
        f"/api/v1/core/usuarios/{uid}", body,
        tenant_id, settings, ("usuarios:write",), http_client,
    )
    return _summarize(data)


# ── Dispatch table mapping tool_name → handler ───────────────────────

_TOOL_HANDLERS = {
    "consultar_ventas": _handle_consultar_ventas,
    "consultar_productos": _handle_consultar_productos,
    "modificar_producto": _handle_modificar_producto,
    "eliminar_producto": _handle_eliminar_producto,
    "crear_producto": _handle_crear_producto,
    "consultar_categorias": _handle_consultar_categorias,
    "crear_categoria": _handle_crear_categoria,
    "modificar_categoria": _handle_modificar_categoria,
    "eliminar_categoria": _handle_eliminar_categoria,
    "consultar_clientes": _handle_consultar_clientes,
    "crear_cliente": _handle_crear_cliente,
    "modificar_cliente": _handle_modificar_cliente,
    "consultar_metricas": _handle_consultar_metricas,
    "consultar_comandas": _handle_consultar_comandas,
    "cambiar_estado_comanda": _handle_cambiar_estado_comanda,
    "consultar_mesas": _handle_consultar_mesas,
    "crear_mesa": _handle_crear_mesa,
    "modificar_mesa": _handle_modificar_mesa,
    "eliminar_mesa": _handle_eliminar_mesa,
    "consultar_modifier_groups": _handle_consultar_modifier_groups,
    "crear_modifier_group": _handle_crear_modifier_group,
    "consultar_reservaciones": _handle_consultar_reservaciones,
    "crear_reservacion": _handle_crear_reservacion,
    "modificar_reservacion": _handle_modificar_reservacion,
    "cancelar_reservacion": _handle_cancelar_reservacion,
    "consultar_disponibilidad_mesas": _handle_consultar_disponibilidad_mesas,
    "consultar_equipo": _handle_consultar_equipo,
    "modificar_usuario": _handle_modificar_usuario,
}
