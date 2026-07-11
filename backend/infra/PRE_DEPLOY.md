# PRE-DEPLOY — Migraciones pendientes de aplicar (multi-rubro F3–F7)

> Estas migraciones son **aditivas** (no destructivas) y **NO han sido aplicadas en prod**.
> Aplicarlas **en orden** ANTES de deployar `api_execute` con los cambios multi-rubro.
> Guardrail vigente: este repo NUNCA aplica migraciones ni deploya; esto es solo el checklist.

## Orden de aplicación

| # | Archivo | Qué agrega | Fase | Riesgo |
|---|---|---|---|---|
| 022 | `022_producto_stock_minimo.sql` | `productos.stock_minimo` (default 0). Alerta de stock bajo. | F3 | Aditiva, RLS ya cubierta |
| 023 | `023_comanda_estado_generico.sql` | Expande el CHECK de `comandas.estado` (agrega `EN_PROCESO`) para el FSM genérico. | F4 | Aditiva (expand CHECK) |
| 024 | `024_recurso_generico.sql` | `mesas.tipo` (default `'mesa'`) para el recurso genérico por rubro. | F5 | Aditiva, default preserva restaurante |
| 025 | `025_cliente_subentidades.sql` | Tabla `cliente_subentidades` (+ política RLS `tenant_isolation`). Módulo SUB_ENTIDAD. | F6 | Tabla nueva con RLS |
| 026 | `026_producto_unidad_venta.sql` | `productos.unidad_venta` (default `'unidad'`). Módulo PRECIO_MEDIDA. El SELECT del catálogo IA ya la referencia → **026 es obligatoria antes de deployar api_execute**. | F6/M4 | Aditiva, default preserva restaurante |

Restaurante queda byte-idéntico: todos los defaults (`'mesa'`, `'unidad'`, `stock_minimo=0`)
reproducen el comportamiento previo; los módulos nuevos se gatean por rubro en el código.

## Deuda diferida (EXCLUIDA de este ciclo — requiere decisión/migración pesada)

- **Cantidad decimal en `comanda_items`**: cobrar por peso/medida en comandas exige cambiar el
  tipo de `cantidad` (INT→NUMERIC) y su lógica → migración pesada + revisión de todo el flujo de
  comanda. El helper puro `precio_medida.subtotal_medida` ya está listo para cuando se haga.
  Hoy PRECIO_MEDIDA solo aplica a cotización/catálogo, no a la comanda.
- **Rename `mesas`→`recursos`** (F5-contract): rename destructivo de tabla + FKs
  (`Session.mesa_id`, `Reservacion.mesa_id`) + enum → EXCLUIDO. Se usa `mesas.tipo` como capa
  de compatibilidad. Contract diferido a post-piloto.
- **Revisión humana por confianza en la ruta orquestada** (R6): requiere flag por-tenant
  `revisar_siempre` en `AgenteConfig` (migración) o una señal de confianza real de la generación.
  Ver `AI_dialer/app/services/chat_service.py` (`_ORCHESTRATED_CONFIANZA`).
