# Sudamérica AI Resto — Plan de Reestructuración para Nicho Gastronómico

> **Versión**: 1.0 — 2026-03-13
> **Autor**: Benjamín Abarca + Claude (Sudamérica AI)
> **Estado**: Aprobado para desarrollo

---

## 1. Visión

Transformar Sudamérica AI de un CRM genérico con skin de restaurante a **la plataforma operativa integral para restaurantes en Latinoamérica**. El software debe cubrir desde que un cliente manda un WhatsApp pidiendo una hamburguesa, hasta que el cocinero la prepara y el dueño ve cuánto ganó ese día.

**Propuesta de valor**: "Tu restaurante con IA — desde el pedido hasta la cocina, sin papel."

---

## 2. Los 4 Pilares (Arquitectura de Producto)

El frontend se reorganiza en 4 pilares que reflejan cómo piensa un dueño de restaurante:

```
┌─────────────────────┬──────────────────────────┬─────────────────────────────────────────┐
│ Pilar               │ Módulos Técnicos         │ Función para el Restaurante             │
├─────────────────────┼──────────────────────────┼─────────────────────────────────────────┤
│ 1. El Recepcionista │ AI_dialer, EvolutionAPI, │ Atiende WhatsApp, toma pedidos,         │
│    (IA)             │ Knowledge, Classifier    │ responde preguntas y reserva mesas.     │
│                     │                          │                                         │
│ 2. El Centro de     │ comandas, KDS, ventas,   │ Una sola pantalla donde caen todos      │
│    Control          │ mesas/delivery           │ los pedidos (Chat, Mesa, Delivery).      │
│                     │                          │                                         │
│ 3. La Despensa      │ productos, categorias,   │ Donde configuran su carta/menú,         │
│                     │ modifiers, inventory     │ combos y marcan lo que se agotó.         │
│                     │                          │                                         │
│ 4. El Contador      │ metricas, ventas,        │ "¿Cuánto vendí hoy?" y pago de          │
│                     │ fidelización, Stripe     │ suscripción. Todo en 1 pantalla.         │
└─────────────────────┴──────────────────────────┴─────────────────────────────────────────┘
```

---

## 3. Cambios Conceptuales (Rebrand del Dominio)

| Concepto Actual (CRM Genérico) | Concepto Nuevo (Gastronómico)     | Impacto Técnico                                           |
|--------------------------------|-----------------------------------|-----------------------------------------------------------|
| `leads`                        | **Clientes** (Frecuentes)        | Rename en frontend, FSM nuevo, tabla se mantiene          |
| `productos`                    | **Platos / Items de Carta**      | + tabla `product_modifiers`, campo `tipo_item`            |
| `categorias`                   | **Secciones de Carta**           | Rename frontend: Entradas, Fondos, Bebidas, Postres       |
| `ventas`                       | **Caja Digital / Órdenes**       | + campo `tipo_entrega`, `numero_mesa`, `estado_comanda`   |
| `leads.estado` FSM             | **Ciclo del Cliente**            | `NUEVO → OCASIONAL → FRECUENTE → VIP \| INACTIVO`        |
| `pipeline` (Kanban)            | **Centro de Control / Comandas** | Kanban de órdenes, no de leads                            |
| `sales_targets`                | **Metas del Local**              | Fusionar con métricas en 1 sola vista                     |
| `prospectos`                   | **Conversaciones IA**            | Rebrand: ya no son "prospectos", son clientes chateando   |

### Nuevo FSM de Clientes (reemplaza Lead FSM)

```
NUEVO ──→ OCASIONAL ──→ FRECUENTE ──→ VIP
  │                        │              │
  └────────────────────────┴──────────────┴──→ INACTIVO
```

- **NUEVO**: Primer contacto (1 interacción)
- **OCASIONAL**: 2-5 pedidos en últimos 90 días
- **FRECUENTE**: 6+ pedidos en últimos 90 días, o 3+ pedidos del mismo plato
- **VIP**: Gasto acumulado > umbral configurable por tenant, o marcado manualmente
- **INACTIVO**: Sin interacción en 60+ días (reactivable)

Transiciones automáticas basadas en historial de órdenes (no manuales como el FSM actual).

---

## 4. Nuevos Módulos Técnicos

### 4.1 Modificadores de Platos (`product_modifiers`)

**Problema**: Un restaurante no vende "Hamburguesa" a secas. Vende "Hamburguesa sin cebolla, extra queso, tamaño XL".

**Modelo de datos**:

```sql
CREATE TABLE modifier_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    nombre VARCHAR(100) NOT NULL,           -- "Extras", "Quitar ingrediente", "Tamaño"
    tipo VARCHAR(20) NOT NULL,              -- SINGLE_SELECT | MULTI_SELECT
    obligatorio BOOLEAN DEFAULT false,
    max_selecciones INT DEFAULT NULL,       -- NULL = sin límite
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE modifiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    grupo_id UUID NOT NULL REFERENCES modifier_groups(id),
    nombre VARCHAR(100) NOT NULL,           -- "Extra queso", "Sin cebolla", "Tamaño XL"
    precio_delta DECIMAL(10,2) DEFAULT 0,   -- +500, -0, +1500
    activo BOOLEAN DEFAULT true,
    orden INT DEFAULT 0
);

-- Relación M:N entre productos y grupos de modificadores
CREATE TABLE producto_modifier_groups (
    producto_id UUID NOT NULL REFERENCES productos(id),
    modifier_group_id UUID NOT NULL REFERENCES modifier_groups(id),
    PRIMARY KEY (producto_id, modifier_group_id)
);
```

**Ejemplo real**:
- Producto: "Hamburguesa Clásica" ($6.990)
- Grupo "Extras" (MULTI_SELECT): Extra queso (+$990), Extra tocino (+$1.490), Huevo (+$790)
- Grupo "Quitar" (MULTI_SELECT): Sin cebolla ($0), Sin tomate ($0), Sin pickle ($0)
- Grupo "Tamaño" (SINGLE_SELECT, obligatorio): Normal ($0), XL (+$2.000)

**Endpoints nuevos en api_execute**:
- `GET/POST /api/v1/core/modifier-groups` — CRUD de grupos
- `GET/POST /api/v1/core/modifiers` — CRUD de modificadores
- `PATCH /api/v1/core/productos/{id}/modifier-groups` — Asignar grupos a producto

**Impacto en AI_dialer**: El Cotizador debe entender modificadores. Cuando un cliente dice "hamburguesa sin cebolla, extra queso", la IA debe:
1. Identificar el producto base
2. Mapear "sin cebolla" → modifier "Sin cebolla" ($0)
3. Mapear "extra queso" → modifier "Extra queso" (+$990)
4. Calcular total: $6.990 + $990 = $7.980

---

### 4.2 Comandas / KDS (Kitchen Display System)

**Problema**: El chat toma un pedido por WhatsApp, pero ¿quién lo prepara? Sin el flujo de cocina, el restaurante sigue necesitando papel o otra app.

**Modelo de datos**:

```sql
CREATE TABLE comandas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    venta_id UUID REFERENCES ventas(id),           -- Vinculada a la venta/orden
    cliente_id UUID REFERENCES leads(id),           -- Cliente (antes "lead")
    tipo_entrega VARCHAR(20) NOT NULL,              -- MESA | DELIVERY | RETIRO
    numero_mesa INT,                                -- NULL si es delivery/retiro
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE', -- PENDIENTE → EN_COCINA → LISTO → ENTREGADO → CANCELADO
    canal_origen VARCHAR(20) NOT NULL,              -- WHATSAPP | WEB | PRESENCIAL
    notas TEXT,                                     -- "Sin cebolla ya lo pedí por chat"
    prioridad INT DEFAULT 0,                        -- 0=normal, 1=urgente
    tiempo_estimado_min INT,                        -- Minutos estimados de preparación
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    entregado_at TIMESTAMPTZ                        -- Timestamp de entrega real
);

CREATE TABLE comanda_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comanda_id UUID NOT NULL REFERENCES comandas(id),
    producto_id UUID NOT NULL REFERENCES productos(id),
    cantidad INT NOT NULL DEFAULT 1,
    precio_unitario DECIMAL(10,2) NOT NULL,
    modifiers_json JSONB DEFAULT '[]',              -- [{modifier_id, nombre, precio_delta}]
    subtotal DECIMAL(10,2) NOT NULL,                -- Server-computed
    notas TEXT                                       -- Notas específicas del item
);
```

**FSM de Comanda**:
```
PENDIENTE ──→ EN_COCINA ──→ LISTO ──→ ENTREGADO
    │              │           │
    └──────────────┴───────────┴──→ CANCELADO
```

**Endpoints nuevos en api_execute**:
- `GET /api/v1/core/comandas` — Lista de comandas (filtro por estado, fecha)
- `POST /api/v1/core/comandas` — Crear comanda (manual o desde venta)
- `PATCH /api/v1/core/comandas/{id}/estado` — Transicionar estado (FSM validado)
- `GET /api/v1/core/comandas/kds` — Vista KDS (solo PENDIENTE + EN_COCINA, ordenadas por prioridad y tiempo)

**Pantalla KDS (Frontend)**:
- 3 columnas: PENDIENTE | EN_COCINA | LISTO
- Cards con: items, modificadores, mesa/delivery, tiempo transcurrido
- Colores: verde (<10min), amarillo (10-20min), rojo (>20min)
- Click para avanzar estado
- **WebSocket** para actualizaciones en tiempo real (nuevo pedido = notificación sonora)
- Diseñado para tablet/pantalla de cocina (responsive, botones grandes)

**Integración con AI_dialer**: Cuando el Cotizador confirma un pedido por WhatsApp:
1. Crea una `venta` con los items
2. Crea automáticamente una `comanda` vinculada con `canal_origen=WHATSAPP`
3. La comanda aparece inmediatamente en el KDS de cocina

---

### 4.3 Módulo de Entrenamiento IA

**Problema**: El dueño no puede corregir a la IA sin contactar a soporte. Necesita una interfaz donde le "enseñe" cosas: "el sushi ya no tiene descuento los martes", "tenemos nuevo plato del día".

**Implementación**: Extender `tenant_knowledge` + UI conversacional.

**Endpoints nuevos**:
- `POST /api/v1/ai/knowledge/teach` — El dueño escribe una instrucción en lenguaje natural; el backend la parsea, genera embedding y la guarda en `tenant_knowledge`
- `GET /api/v1/ai/knowledge` — Lista de conocimientos enseñados (con opción de editar/eliminar)
- `POST /api/v1/ai/knowledge/test` — "Pregúntale algo a tu IA" — envía un mensaje de prueba y muestra la respuesta sin enviársela al cliente
- `DELETE /api/v1/ai/knowledge/{id}` — Eliminar conocimiento

**Flujo UX**:
```
┌──────────────────────────────────────────────────┐
│  Entrenar a tu Asistente IA                      │
├──────────────────────────────────────────────────┤
│                                                  │
│  "Enséñale algo nuevo:"                          │
│  ┌──────────────────────────────────────────┐    │
│  │ El menú ejecutivo ahora cuesta $8.990    │    │
│  │ de lunes a viernes. Los sábados no hay   │    │
│  │ menú ejecutivo.                          │    │
│  └──────────────────────────────────────────┘    │
│  [Guardar]                                       │
│                                                  │
│  "Prueba preguntándole:"                         │
│  ┌──────────────────────────────────────────┐    │
│  │ ¿Cuánto cuesta el menú ejecutivo?        │    │
│  └──────────────────────────────────────────┘    │
│  [Probar]                                        │
│                                                  │
│  IA: "El menú ejecutivo cuesta $8.990 y está     │
│   disponible de lunes a viernes."                │
│                                                  │
│  Conocimientos guardados:                        │
│  ✓ Menú ejecutivo $8.990 L-V (hace 2 min)       │
│  ✓ No hay descuento sushi martes (hace 1h)       │
│  ✓ Horario: L-S 12:00-23:00, D cerrado (ayer)   │
└──────────────────────────────────────────────────┘
```

---

### 4.4 Fidelización de Clientes

**Problema**: "Leads" y "pipeline" no tienen sentido para un restaurante local. Lo que importa es: ¿quién vuelve? ¿qué pide siempre? ¿cuánto ha gastado?

**Nuevo modelo (extensión de `leads` → `clientes`)**:

```sql
-- Campos nuevos en tabla leads (ALTER TABLE, no nueva tabla)
ALTER TABLE leads ADD COLUMN total_pedidos INT DEFAULT 0;
ALTER TABLE leads ADD COLUMN total_gastado DECIMAL(12,2) DEFAULT 0;
ALTER TABLE leads ADD COLUMN plato_favorito VARCHAR(200);
ALTER TABLE leads ADD COLUMN ultima_visita TIMESTAMPTZ;
ALTER TABLE leads ADD COLUMN frecuencia_dias DECIMAL(5,1);  -- Promedio días entre pedidos
ALTER TABLE leads ADD COLUMN tags JSONB DEFAULT '[]';        -- ["vegano", "alérgico maní", "cumpleaños marzo"]
```

**Actualización automática**: Un trigger o servicio que después de cada comanda ENTREGADA:
1. Incrementa `total_pedidos`
2. Suma al `total_gastado`
3. Recalcula `plato_favorito` (el más pedido)
4. Actualiza `ultima_visita`
5. Recalcula `frecuencia_dias`
6. Auto-transiciona el estado FSM (NUEVO→OCASIONAL→FRECUENTE→VIP)

**Vista Frontend**: Reemplaza el Kanban de pipeline por una vista de "Clientes Frecuentes":
- Tarjetas de cliente con: nombre, foto (si tiene WhatsApp), plato favorito, frecuencia, gasto total
- Filtros: VIP, Frecuentes, Inactivos (para re-engagement)
- Acción rápida: "Enviar promo a VIPs" → dispara mensaje por WhatsApp

**Impacto en AI_dialer (Seguimiento)**: Cuando un VIP escribe por WhatsApp, la IA dice:
> "¡Hola Juanito! ¿Lo de siempre? (Pizza Margherita familiar + Coca-Cola 1.5L = $14.980)"

---

## 5. Fases de Desarrollo

### FASE 1 — "La Cocina Funciona" (Core Operativo)

**Objetivo**: Que un restaurante pueda recibir un pedido por WhatsApp y que aparezca en una pantalla de cocina. Sin esto, es demo. Con esto, es producto.

**Duración estimada**: 3-4 sprints

#### Entregables

| # | Tarea                                    | Servicio        | Tipo              | Prioridad |
|---|------------------------------------------|-----------------|-------------------|-----------|
| 1 | Tabla `modifier_groups` + `modifiers` + `producto_modifier_groups` | api_execute | Backend (modelo + CRUD) | P0 |
| 2 | Endpoints CRUD modifier groups/modifiers  | api_execute     | Backend (routes)  | P0        |
| 3 | UI de Carta con modificadores             | frontend    | Frontend          | P0        |
| 4 | Tabla `comandas` + `comanda_items`        | api_execute     | Backend (modelo)  | P0        |
| 5 | Endpoints CRUD comandas + FSM             | api_execute     | Backend (routes)  | P0        |
| 6 | Pantalla KDS (Kitchen Display System)     | frontend    | Frontend          | P0        |
| 7 | WebSocket para KDS real-time              | api_execute     | Backend + Frontend| P1        |
| 8 | Cotizador entiende modificadores          | AI_dialer       | Backend (IA)      | P0        |
| 9 | Cotizador crea comanda automáticamente    | AI_dialer       | Backend (IA)      | P0        |
| 10| Campo `tipo_entrega` + `numero_mesa` en ventas | api_execute | Backend (schema) | P0       |
| 11| Rebrand "Productos" → "Carta" en frontend | frontend   | Frontend          | P1        |
| 12| SQL migrations (DDL manual en Cloud SQL)  | infra           | DBA               | P0        |

#### Resultado Esperado Fase 1
- Un restaurante configura su carta con platos y modificadores
- Un cliente escribe por WhatsApp: "Quiero una hamburguesa sin cebolla para delivery"
- La IA identifica: producto + modificador + tipo entrega
- Se crea la orden y aparece automáticamente en la pantalla de cocina
- El cocinero toca "En cocina" → "Listo" → "Entregado"
- **Demo killer**: Mostrar en vivo cómo un mensaje de WhatsApp se convierte en una comanda en la cocina en <10 segundos

---

### FASE 2 — "El Restaurante Inteligente" (Diferenciación IA)

**Objetivo**: La IA deja de ser un chatbot genérico y se convierte en un empleado que conoce la carta, los clientes y las reglas del negocio.

**Duración estimada**: 2-3 sprints

#### Entregables

| # | Tarea                                    | Servicio        | Tipo              | Prioridad |
|---|------------------------------------------|-----------------|-------------------|-----------|
| 1 | Módulo Entrenamiento IA (teach/test/list) | AI_dialer + api_execute | Backend   | P0        |
| 2 | UI de Entrenamiento IA                    | frontend    | Frontend          | P0        |
| 3 | Campos fidelización en `leads` (ALTER TABLE) | api_execute  | Backend (schema)  | P0        |
| 4 | Servicio de actualización automática post-comanda | api_execute | Backend     | P0        |
| 5 | Nuevo FSM: NUEVO→OCASIONAL→FRECUENTE→VIP→INACTIVO | shared | Backend (enum) | P0        |
| 6 | Vista "Clientes Frecuentes" (reemplaza pipeline) | frontend | Frontend   | P0        |
| 7 | Seguimiento personalizado ("lo de siempre, Juanito?") | AI_dialer | Backend (IA) | P1    |
| 8 | Rebrand leads→clientes en todo el frontend | frontend  | Frontend          | P1        |
| 9 | Fusionar sales_targets + métricas en 1 vista | frontend | Frontend         | P1        |
| 10| Intent COMANDA nuevo en classifier        | AI_dialer       | Backend (IA)      | P1        |

#### Resultado Esperado Fase 2
- El dueño abre "Entrenar IA", escribe "Ya no tenemos salmón los lunes", y la IA deja de ofrecer salmón los lunes
- El dueño ve sus "Clientes VIP" con plato favorito y gasto total
- Cuando Juanito (VIP) escribe, la IA le dice "¿Lo de siempre?" con su pedido favorito precargado
- El dueño tiene UNA pantalla con sus metas y resultados del día/semana/mes
- **Demo killer**: Entrenar a la IA en vivo y mostrar que responde distinto inmediatamente

---

### FASE 3 — "El Local Profesional" (Escala y Hardware)

**Objetivo**: Integración con el mundo físico del restaurante. Impresión, mesas, delivery, integraciones externas.

**Duración estimada**: 3-4 sprints

#### Entregables

| # | Tarea                                    | Servicio        | Tipo              | Prioridad |
|---|------------------------------------------|-----------------|-------------------|-----------|
| 1 | Impresión de comandas (PDF/imagen para imprimir desde browser) | frontend | Frontend | P1 |
| 2 | Integración PrintNode / QZ Tray (impresora térmica) | Nuevo servicio o api_execute | Backend | P2 |
| 3 | Gestión de Mesas (floor plan básico)      | api_execute + frontend | Fullstack | P1 |
| 4 | Integración delivery (PedidosYa API, Rappi) | tasks          | Backend           | P2        |
| 5 | Inventario real (stock por producto, alertas de agotado) | api_execute | Backend   | P1        |
| 6 | IA sugiere "combo" cuando detecta oportunidad | AI_dialer    | Backend (IA)      | P2        |
| 7 | Notificaciones push (comanda lista → garzón) | tasks + frontend | Fullstack     | P1        |
| 8 | Reportes avanzados (heatmap horas punta, plato más vendido por día) | api_execute | Backend | P1 |
| 9 | Multi-local (1 tenant, N sucursales)      | shared + api_execute | Backend       | P2        |

#### Resultado Esperado Fase 3
- La comanda se imprime automáticamente en la cocina al confirmarse el pedido
- El dueño ve un mapa de mesas y sabe cuáles están ocupadas
- Pedidos de PedidosYa/Rappi caen al mismo Centro de Control
- El dueño ve: "Los viernes entre 20:00-21:00 es tu hora punta, tu plato estrella es la Hamburguesa Clásica"
- **Demo killer**: Pedido por WhatsApp → se imprime en cocina → cliente recibe "Tu pedido está listo" por WhatsApp

---

## 6. Cambios en Arquitectura de Servicios

### Estado Actual (5 servicios)
```
api_execute(:8000)     — REST/CRUD/Auth
AI_dialer(:8001)       — LLM/IA
callback_manual(:8002) — Revisión humana
tasks(:8003)           — Tareas async
canales_service(:8004) — WhatsApp/Evolution
```

### Estado Post-Reestructuración (mismos 5 servicios, responsabilidades ampliadas)

```
api_execute(:8000)     — + Comandas CRUD, Modifiers CRUD, Fidelización, KDS endpoint
AI_dialer(:8001)       — + Cotizador con modifiers, Training endpoint, Seguimiento VIP
callback_manual(:8002) — Sin cambios (sigue siendo human-in-the-loop)
tasks(:8003)           — + Notificaciones push, PrintNode relay (Fase 3)
canales_service(:8004) — Sin cambios (WhatsApp + webhooks)
```

**No se crean servicios nuevos.** El KDS es un endpoint + WebSocket en api_execute, y una página nueva en el frontend.

---

## 7. Cambios en Base de Datos (DDL)

### Tablas Nuevas (Fase 1)
- `modifier_groups` — Grupos de modificadores por tenant
- `modifiers` — Opciones dentro de cada grupo
- `producto_modifier_groups` — Relación M:N productos ↔ grupos
- `comandas` — Órdenes de cocina con FSM
- `comanda_items` — Items de cada comanda con modificadores

### Columnas Nuevas (Fase 2)
- `leads.total_pedidos` INT
- `leads.total_gastado` DECIMAL(12,2)
- `leads.plato_favorito` VARCHAR(200)
- `leads.ultima_visita` TIMESTAMPTZ
- `leads.frecuencia_dias` DECIMAL(5,1)
- `leads.tags` JSONB

### Tablas Nuevas (Fase 3)
- `mesas` — Mesas del local (numero, capacidad, zona, activo)
- `inventario_movimientos` — Log de stock (entrada/salida/merma)

### Migración
- **NO hay Alembic.** Todos los DDL se ejecutan manualmente en Cloud SQL.
- Los scripts se guardan en `backend/infra/sql/` con numeración secuencial.
- Archivo: `backend/infra/sql/005_resto_fase1.sql` (Fase 1)
- Archivo: `backend/infra/sql/006_resto_fase2.sql` (Fase 2)
- Archivo: `backend/infra/sql/007_resto_fase3.sql` (Fase 3)

---

## 8. Cambios en Frontend (Navegación)

### Sidebar Actual
```
Dashboard
Pipeline (Kanban leads)
Leads
Productos
Ventas
IA
Prospectos
Equipo
Configuración
Reportes
ROI
Calendario
```

### Sidebar Nuevo (Post-Fase 2)
```
── EL RECEPCIONISTA ──
  Conversaciones IA        (antes "Prospectos")
  Entrenar IA              (NUEVO)
  Revisión Humana          (antes en callback_manual)

── CENTRO DE CONTROL ──
  Comandas / KDS           (NUEVO)
  Órdenes del Día          (antes "Ventas")

── LA DESPENSA ──
  Carta & Menú             (antes "Productos" + "Categorias")
  Modificadores            (NUEVO)

── EL CONTADOR ──
  Resumen del Día          (antes "Dashboard")
  Clientes Frecuentes      (antes "Leads" + "Pipeline")
  Metas & Reportes         (fusión "Reportes" + "ROI" + "Sales Targets")

── CONFIGURACIÓN ──
  Mi Local                 (antes "Configuración")
  Equipo                   (sin cambios)
```

---

## 9. Cambios en IA (Intents y Sub-Agentes)

### Intents del Classifier (actualizado)

| Intent      | Sub-Agente  | Ejemplo                                        |
|-------------|-------------|------------------------------------------------|
| PEDIDO      | COTIZADOR   | "Quiero 2 hamburguesas sin cebolla"            |
| MENU        | COTIZADOR   | "¿Qué tienen para almorzar?"                   |
| COTIZACION  | COTIZADOR   | "¿Cuánto sale un combo para 4 personas?"        |
| RESERVA     | RAG         | "Quiero reservar mesa para 6 el viernes a las 9"|
| DELIVERY    | COTIZADOR   | "¿Hacen delivery a Providencia?"                |
| ESTADO      | SEGUIMIENTO | "¿Ya está mi pedido?" (NUEVO intent)            |
| FIDELIDAD   | SEGUIMIENTO | "¿Cuál fue mi último pedido?" (NUEVO intent)    |
| HORARIO     | RAG         | "¿A qué hora abren?"                            |
| CONSULTA    | RAG         | "¿Tienen opciones veganas?"                     |
| QUEJA       | RAG         | "La comida llegó fría"                          |
| OTRO        | RAG         | Cualquier cosa no clasificada                   |

### Cambios en Sub-Agentes

**Cotizador** (ampliado):
- Entiende modificadores ("sin cebolla" → busca modifier en grupo "Quitar")
- Pregunta tipo de entrega: "¿Es para comer acá, delivery o retiro?"
- Si es mesa: "¿Número de mesa?"
- Al confirmar: crea venta + comanda automáticamente
- Calcula subtotales incluyendo precio_delta de modificadores

**Seguimiento** (ampliado):
- Detecta clientes VIP por teléfono/nombre
- Ofrece "lo de siempre" basado en `plato_favorito`
- Para intent ESTADO: consulta `comandas` del cliente y reporta estado actual
- Para intent FIDELIDAD: muestra historial de pedidos recientes

---

## 10. Métricas de Éxito por Fase

### Fase 1
- [ ] Un pedido por WhatsApp genera una comanda en KDS en <10 segundos
- [ ] El cocinero puede transicionar estados sin salir de la pantalla KDS
- [ ] La carta soporta al menos 3 grupos de modificadores por plato
- [ ] 100% de tests passing, coverage ≥ 70%
- [ ] Demo exitosa a 3 restaurantes piloto

### Fase 2
- [ ] El dueño puede entrenar a la IA en <1 minuto (teach + test)
- [ ] El sistema identifica automáticamente clientes frecuentes y VIPs
- [ ] La IA personaliza la bienvenida para clientes recurrentes
- [ ] Vista unificada de métricas del día (ventas, comandas, top platos)
- [ ] NPS de dueños piloto ≥ 8/10

### Fase 3
- [ ] Comandas se imprimen en cocina sin intervención manual
- [ ] Pedidos de 2+ plataformas delivery caen al mismo Centro de Control
- [ ] El dueño ve heatmap de horas punta y plato estrella por día
- [ ] Soporte multi-local (al menos 2 sucursales para 1 tenant piloto)

---

## 11. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| WebSocket en Cloud Run (timeout 60min) | Alta | Medio | Fallback a polling cada 5s en KDS; evaluar Cloud Run gen2 |
| Modificadores complejos ("mitad esto, mitad aquello") | Media | Alto | Empezar solo con SINGLE/MULTI_SELECT; "mitad y mitad" va a human review |
| Impresoras térmicas (compatibilidad hardware) | Alta | Alto | Fase 3: empezar con PDF desde browser, luego PrintNode |
| Cloud SQL no tiene auto-migrate | Baja | Alto | Scripts DDL numerados + checklist de deploy |
| Rate limits en LLM (hora punta restaurante = 19:00-21:00) | Media | Alto | Cache de respuestas FAQ, Gemini como fallback de OpenAI |
| El dueño "entrena" mal a la IA | Media | Medio | Validar con test inmediato; permitir revertir cambios |

---

## 12. Archivos Clave a Crear/Modificar

### Fase 1 — Archivos Nuevos
```
backend/api_execute/app/models/modifier.py           — Modelos modifier_groups, modifiers, producto_modifier_groups
backend/api_execute/app/models/comanda.py             — Modelos comandas, comanda_items
backend/api_execute/app/schemas/modifier.py           — Pydantic schemas para modifiers
backend/api_execute/app/schemas/comanda.py            — Pydantic schemas para comandas
backend/api_execute/app/routes/modifiers.py           — CRUD endpoints modificadores
backend/api_execute/app/routes/comandas.py            — CRUD + FSM + KDS endpoints
backend/api_execute/app/services/modifier_svc.py      — Lógica de negocio modificadores
backend/api_execute/app/services/comanda_svc.py       — Lógica de negocio comandas + FSM
backend/shared/models/enums.py                        — + ComandaEstado, TipoEntrega enums
backend/infra/sql/005_resto_fase1.sql                 — DDL para tablas nuevas
frontend/app/(dashboard)/carta/page.tsx           — Vista de Carta con modificadores
frontend/app/(dashboard)/comandas/page.tsx        — Pantalla KDS
frontend/hooks/useModifiers.ts                    — Hook para CRUD modificadores
frontend/hooks/useComandas.ts                     — Hook para CRUD comandas + WebSocket
frontend/components/comandas/KDSBoard.tsx         — Componente KDS (3 columnas)
frontend/components/carta/ModifierEditor.tsx      — Editor de modificadores en carta
```

### Fase 1 — Archivos a Modificar
```
backend/AI_dialer/app/services/cotizador_agent.py     — Soportar modificadores + crear comanda
backend/AI_dialer/app/services/classify_service.py    — Nuevos intents
backend/api_execute/app/main.py                       — Registrar nuevos routers
backend/api_execute/app/routes/ventas.py              — + tipo_entrega, numero_mesa
backend/api_execute/app/models/venta.py               — + tipo_entrega, numero_mesa columns
frontend/components/layout/Sidebar.tsx            — Nueva navegación (4 pilares)
```

### Fase 2 — Archivos Nuevos
```
backend/AI_dialer/app/routes/knowledge.py             — Endpoints teach/test/list
backend/AI_dialer/app/services/training_service.py    — Lógica de entrenamiento
backend/api_execute/app/services/fidelizacion_svc.py  — Cálculo automático de métricas cliente
backend/infra/sql/006_resto_fase2.sql                 — ALTER TABLE leads + nuevos campos
frontend/app/(dashboard)/entrenar-ia/page.tsx     — UI de entrenamiento
frontend/app/(dashboard)/clientes/page.tsx        — Vista Clientes Frecuentes
frontend/hooks/useTraining.ts                     — Hook para teach/test
frontend/hooks/useClientes.ts                     — Hook para clientes (reemplaza useLeads)
frontend/components/training/TrainingChat.tsx     — Chat de entrenamiento
frontend/components/clientes/ClienteCard.tsx      — Tarjeta de cliente frecuente
```

---

## 13. Decisiones Técnicas Tomadas

1. **No se crean servicios nuevos** — KDS es un endpoint en api_execute, no un microservicio aparte. Mantener 5 servicios.
2. **WebSocket para KDS** — Usar `websockets` en FastAPI (api_execute). Cloud Run soporta WebSocket en gen2.
3. **Modifiers como JSONB en comanda_items** — Para preservar el snapshot del modificador al momento del pedido (si cambia el precio después, la comanda histórica no muta).
4. **No eliminar tabla `leads`** — Renombrarla semánticamente en frontend. El backend sigue usando `leads` internamente. Esto evita reescribir queries, RLS policies, y foreign keys.
5. **FSM de clientes automático** — Las transiciones NUEVO→OCASIONAL→FRECUENTE→VIP son calculadas, no manuales. Un servicio post-comanda actualiza los contadores y transiciona.
6. **Impresión térmica = Fase 3** — El MVP funciona con pantalla KDS. La impresora es nice-to-have para la demo.
7. **Floor plan de mesas = Fase 3** — Fase 1 solo necesita `numero_mesa: int`. El mapa visual es complejidad innecesaria para el MVP.

---

## Apéndice A — Glosario Gastronómico → Técnico

| Término del Restaurante | Concepto Técnico        | Tabla/Campo                    |
|--------------------------|-------------------------|--------------------------------|
| Carta / Menú             | Catálogo de productos   | `productos` + `categorias`     |
| Plato                    | Producto                | `productos.nombre`             |
| Combo                    | Producto compuesto      | `productos` con flag `es_combo`|
| Modificador              | Variante de producto    | `modifiers`                    |
| Comanda                  | Orden de cocina         | `comandas`                     |
| Garzón / Mesero          | Usuario rol ASESOR      | `usuarios.role = ASESOR`       |
| Cocinero                 | Usuario rol VIEWER+KDS  | `usuarios` (nuevo permiso)     |
| Dueño                    | Usuario rol ADMIN       | `usuarios.role = ADMIN`        |
| Mesa                     | Ubicación física        | `comandas.numero_mesa`         |
| Delivery                 | Tipo de entrega         | `comandas.tipo_entrega`        |
| Cliente frecuente        | Lead con estado ≥ FRECUENTE | `leads.estado`            |
| "Lo de siempre"          | Plato favorito          | `leads.plato_favorito`         |
