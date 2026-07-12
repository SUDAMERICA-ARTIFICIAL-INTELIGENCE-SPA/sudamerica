"""Central matrix of which internal services may call which resource.

Edit HERE to grant/revoke a service's access — never inline in routes.

Each constant is the ``service_callers`` tuple for one protected resource
(the guard that consumes it is noted in the docstring). Constants are kept
separate per resource even when tuples coincide, so granting one service
access to a resource never silently widens another.
"""

# ─── api_execute: carta (menu) ───

CARTA_READERS: tuple[str, ...] = ("open_agent",)
"""Services that may read menu items (categorias, productos) — CartaReader."""

CARTA_WRITERS: tuple[str, ...] = ("open_agent",)
"""Services that may write menu items — CartaWriter."""

# ─── api_execute: leads ───

LEAD_READERS: tuple[str, ...] = ("canales_service", "open_agent", "callback_manual", "tasks")
"""Services that may read leads — LeadReader."""

LEAD_WRITERS: tuple[str, ...] = ("canales_service", "open_agent")
"""Services that may write leads — LeadWriter."""

# ─── api_execute: ventas ───

VENTA_READERS: tuple[str, ...] = ("open_agent",)
"""Services that may read ventas — VentaReader."""

VENTA_WRITERS: tuple[str, ...] = ("open_agent",)
"""Services that may write ventas — VentaWriter."""

# ─── api_execute: comandas ───

COMANDA_READERS: tuple[str, ...] = ("open_agent",)
"""Services that may read comandas — ComandaReader."""

COMANDA_WRITERS: tuple[str, ...] = ("open_agent",)
"""Services that may write comandas — ComandaWriter."""

# ─── api_execute: modifiers ───

MODIFIER_READERS: tuple[str, ...] = ("open_agent",)
"""Services that may read modifiers — ModifierReader."""

MODIFIER_WRITERS: tuple[str, ...] = ("open_agent",)
"""Services that may write modifiers — ModifierWriter."""

# ─── api_execute: mesas ───

MESA_READERS: tuple[str, ...] = ("open_agent",)
"""Services that may read mesas — MesaReader."""

MESA_WRITERS: tuple[str, ...] = ("open_agent",)
"""Services that may write mesas — MesaWriter."""

# Note: GET /mesas/disponibilidad is a users-only endpoint (AnyAuthenticated).
# No internal service queries it — the admin copilot (open_agent) checks
# availability via GET /reservaciones/disponibilidad. An empty service_callers
# allowlist would mean "any trusted issuer", not "no service", so the route uses
# a plain user guard instead of a service_callers tuple here.

# ─── api_execute: usuarios ───

USUARIO_READERS: tuple[str, ...] = ("open_agent",)
"""Services that may read usuarios — UsuarioReader."""

USUARIO_WRITERS: tuple[str, ...] = ("open_agent",)
"""Services that may write usuarios — UsuarioWriter."""

# ─── api_execute: metricas ───

METRICAS_READERS: tuple[str, ...] = ("open_agent",)
"""Services that may read metricas — MetricasReader."""

# ─── api_execute: AI orchestrator chat proxy ───

ORCHESTRATOR_CHAT_CALLERS: tuple[str, ...] = ("canales_service",)
"""Services that may invoke api_execute's AI chat orchestrator — AiChatActor."""

AGENT_CONFIG_READERS: tuple[str, ...] = ("canales_service",)
"""Services that may read the tenant agent configuration (config:read) — GET /ai/config."""

CONVERSATION_IMPORTERS: tuple[str, ...] = ("canales_service",)
"""Services that may import historical conversation messages
(conversations:import) — POST /ai/conversations/import."""

# ─── canales_service ───

WHATSAPP_SENDERS: tuple[str, ...] = ("tasks", "api_execute")
"""Services that may send WhatsApp messages (whatsapp:send)."""

WEBHOOK_PROCESSORS: tuple[str, ...] = ("tasks",)
"""Services that may invoke internal webhook processing (webhook:process)."""

# ─── callback_manual ───

# Human-review items (reviews:create) are created only by ADMIN/ASESOR users via
# the review panel — no internal service produces them (the orchestrated customer
# chat reports a fixed high confidence, so no low-confidence auto-review is
# generated). The create endpoint uses a plain user-role guard; there is no
# service_callers allowlist to grant here.

# ─── tasks ───

SEND_RESPONSE_CALLERS: tuple[str, ...] = ("callback_manual",)
"""Services that may forward approved AI responses to leads (tasks:send_response)."""
