# Carta & Menu — Bitacora del Modulo

> **Ultima actualizacion**: 2026-03-14
> **Estado**: OPERATIVO (CRUD + Import CSV/PDF/Imagen), EN DESARROLLO (URL scraping + GCS images)
> **Servicio principal**: `api_execute` (:8000) — rutas bajo `/api/v1/core/`
> **Frontend**: `/carta` (frontend)

---

## 1. Estado Actual — Que existe HOY

### 1.1 Entidades del dominio

```
Categoria  ──1:N──  Producto  ──M:N──  ModifierGroup  ──1:N──  Modifier
                        |
                        v
                   ComandaItem  ──N:1──  Comanda
                   (snapshot de modifiers en JSONB)
```

| Entidad | Tabla | Campos clave | RLS |
|---------|-------|-------------|-----|
| Categoria | `categorias` | nombre, descripcion, activo | Si |
| Producto | `productos` | nombre, descripcion, precio, categoria_id, sku, imagen_url, stock, disponible, activo | Si |
| ModifierGroup | `modifier_groups` | nombre, tipo (SINGLE/MULTI_SELECT), obligatorio, max_selecciones | Si |
| Modifier | `modifiers` | nombre, precio_delta, orden, grupo_id | Si |
| ProductoModifierGroup | `producto_modifier_groups` | producto_id, modifier_group_id (M:N join) | No (via FK) |
| Comanda | `comandas` | tipo_entrega, numero_mesa, estado (FSM), canal_origen, prioridad | Si |
| ComandaItem | `comanda_items` | producto_id, cantidad, precio_unitario, modifiers_json (JSONB snapshot), subtotal | No (via FK) |

### 1.2 Endpoints REST

#### Categorias — `/api/v1/core/categorias`
| Metodo | Path | Auth | Funcion |
|--------|------|------|---------|
| POST | `/` | ADMIN | Crear categoria |
| GET | `/` | authenticated | Listar (paginado) |
| GET | `/{id}` | authenticated | Detalle |
| PATCH | `/{id}` | ADMIN | Actualizar parcial |
| DELETE | `/{id}` | ADMIN | Soft-delete (activo=false) |

#### Productos — `/api/v1/core/productos`
| Metodo | Path | Auth | Funcion |
|--------|------|------|---------|
| POST | `/` | ADMIN | Crear producto |
| GET | `/` | user/service | Listar (paginado + filtros) |
| GET | `/{id}` | user/service | Detalle |
| PATCH | `/{id}` | ADMIN | Actualizar parcial |
| DELETE | `/{id}` | ADMIN | Soft-delete |
| PATCH | `/{id}/activar` | ADMIN | Reactivar producto |

**Filtros GET**: `categoria_id`, `precio_min`, `precio_max`, `nombre` (LIKE), `disponible`

#### Modifier Groups — `/api/v1/core/modifier-groups`
| Metodo | Path | Auth | Funcion |
|--------|------|------|---------|
| POST | `/` | ADMIN | Crear grupo (con modifiers inline) |
| GET | `/` | user/service | Listar (paginado + filtro nombre) |
| GET | `/{id}` | user/service | Detalle (con modifiers nested) |
| PATCH | `/{id}` | ADMIN | Actualizar grupo |
| DELETE | `/{id}` | ADMIN | Soft-delete grupo |
| GET | `/{id}/modifiers` | user/service | Listar modifiers del grupo |
| POST | `/{id}/modifiers` | ADMIN | Crear modifier |
| PATCH | `/modifiers/{id}` | ADMIN | Actualizar modifier |
| DELETE | `/modifiers/{id}` | ADMIN | Soft-delete modifier |
| GET | `/productos/{id}` | user/service | Grupos asignados a producto |
| PATCH | `/productos/{id}` | ADMIN | Asignar grupos (REPLACE) |

#### Comandas — `/api/v1/core/comandas`
| Metodo | Path | Auth | Funcion |
|--------|------|------|---------|
| POST | `/` | ASESOR/ADMIN | Crear comanda (precio computado server-side) |
| GET | `/` | user/service | Listar (filtros: estado, tipo_entrega, canal, fecha) |
| GET | `/kds` | user/service | Vista KDS agrupada por estado |
| GET | `/{id}` | user/service | Detalle |
| PATCH | `/{id}/estado` | ASESOR/ADMIN | Transicion FSM |
| DELETE | `/{id}` | ADMIN | Soft-delete |

#### Menu Import — `/api/v1/core/menu`
| Metodo | Path | Auth | Funcion |
|--------|------|------|---------|
| POST | `/import` | ADMIN | Import CSV/PDF/imagen (max 10MB) |

### 1.3 Archivos del modulo

```
backend/api_execute/
├── app/
│   ├── models/
│   │   ├── categoria.py        # SQLAlchemy model
│   │   ├── producto.py         # SQLAlchemy model + FK categoria
│   │   ├── modifier.py         # ModifierGroup + Modifier + ProductoModifierGroup
│   │   └── comanda.py          # Comanda + ComandaItem
│   ├── schemas/
│   │   ├── categoria.py        # Create/Update/Response DTOs
│   │   ├── producto.py         # Create/Update/Response/Filter DTOs
│   │   ├── modifier.py         # Group + Modifier + Assign DTOs
│   │   └── comanda.py          # Comanda + Items + Transicion DTOs
│   ├── routes/
│   │   ├── categorias.py       # REST endpoints
│   │   ├── productos.py        # REST endpoints + filtros
│   │   ├── modifiers.py        # REST endpoints + M:N assignment
│   │   ├── comandas.py         # REST endpoints + KDS + FSM
│   │   └── menu_import.py      # File upload + routing CSV vs AI
│   └── services/
│       ├── categoria_svc.py    # CRUD + soft-delete
│       ├── producto_svc.py     # CRUD + filtros + reactivar + _escape_like()
│       ├── modifier_svc.py     # CRUD + assign (replace) + inline creation
│       ├── comanda_svc.py      # CRUD + FSM + KDS + price computation
│       ├── menu_import_svc.py  # CSV parser + AI extraction (Gemini Vision)
│       └── fidelizacion_svc.py # Stats update on comanda delivery
└── tests/
    ├── test_categorias.py      # 5 tests
    ├── test_productos.py       # 10 tests
    ├── test_menu_import.py     # 11 tests (CSV + AI parser)
    ├── test_comanda_notify.py  # 4 tests
    └── test_fidelizacion.py    # 4 tests

frontend/
├── app/(dashboard)/
│   ├── carta/page.tsx          # Tab "Platos" + Tab "Modificadores" (554 lineas)
│   └── productos/page.tsx      # Vista tabla alternativa (72 lineas)
├── components/
│   ├── carta/
│   │   ├── MenuImportModal.tsx # Dropzone CSV/PDF/imagen (156 lineas)
│   │   └── ModifierEditor.tsx  # CRUD modifier groups (385 lineas)
│   └── productos/
│       ├── ProductoForm.tsx    # Modal crear/editar producto (152 lineas)
│       └── ProductosTable.tsx  # Tabla paginada (190 lineas)
├── hooks/
│   ├── useProductos.ts         # CRUD hooks (116 lineas)
│   ├── useCategorias.ts        # CRUD hooks (89 lineas)
│   ├── useModifiers.ts         # CRUD hooks + assign (168 lineas)
│   └── useMenuImport.ts        # Upload hook (70 lineas)
└── lib/
    ├── types.ts                # Producto, Categoria, ModifierGroup, Modifier interfaces
    └── enums.ts                # ModifierGroupTipo enum

backend/infra/
├── 001_schema.sql              # categorias, productos (tablas base)
└── sql/005_resto_fase1.sql     # modifier_groups, modifiers, producto_modifier_groups, comandas, comanda_items + RLS
```

### 1.4 Tests existentes

| Archivo | Tests | Cobertura |
|---------|-------|-----------|
| `test_categorias.py` | 5 | CRUD completo |
| `test_productos.py` | 10 | CRUD + filtros + toggle disponible + reactivar |
| `test_menu_import.py` | 11 | CSV (6 tests) + AI parser (5 tests) |
| `test_comanda_notify.py` | 4 | Notificaciones de comanda |
| `test_fidelizacion.py` | 4 | Stats post-entrega |
| **TOTAL** | **34** | --- |

#### GAPS de testing (sin tests):
- **modifier_svc.py** — 0 tests (CRUD, inline creation, assign/replace)
- **comanda_svc.py** — 0 tests (create con precio computado, FSM transitions, KDS view)
- **modifiers.py routes** — 0 tests (11 endpoints sin coverage)
- **comandas.py routes** — 0 tests (6 endpoints sin coverage)
- **import_from_ai()** — 0 tests (solo se testea `_parse_ai_response`, no la llamada a Gemini)

### 1.5 Logica de negocio clave

#### Precio computado en comandas (comanda_svc.create_comanda)
```
precio_unitario = producto.precio + SUM(modifier.precio_delta)
subtotal = precio_unitario * cantidad
modifiers_json = SNAPSHOT [{modifier_id, nombre, precio_delta}, ...]
```
- El precio se congela al momento de crear la comanda
- Cambios futuros de precio NO afectan comandas existentes
- Los modifiers se guardan como JSONB snapshot (no relacion)

#### FSM de Comanda
```
PENDIENTE → EN_COCINA → LISTO → ENTREGADO
    |           |         |
    └───────────┴─────────┴───→ CANCELADO
```
- Al llegar a ENTREGADO: se setea `entregado_at` + se actualiza fidelizacion del lead
- Transiciones invalidas devuelven 422

#### Assign Modifier Groups (replace)
- `assign_modifier_groups_to_product()` BORRA todas las asignaciones existentes y crea las nuevas
- No es merge, es replace completo
- Si se pasa array vacio, se desasignan todos los grupos

#### Menu Import con AI
- Soporta: CSV, PDF, PNG, JPG, WebP (max 10MB)
- AI: Gemini Vision via OpenAI-compatible endpoint
- Prompt detecta categorias reales del documento, maneja variantes con tamanos
- `_bulk_create()` reutiliza categorias existentes (lookup case-insensitive)

---

## 2. Diagnostico — Que falta

### 2.1 Features ausentes (priorizadas)

| # | Feature | Impacto | Complejidad | Prerequisito de |
|---|---------|---------|-------------|-----------------|
| F1 | **Upload de imagenes a GCS** | Alto — sin imagenes el menu se ve pobre | Media | F2, F3 |
| F2 | **Import desde URL (web scraping)** | Alto — onboarding killer ("pega tu link") | Alta | F1 |
| F3 | **Imagenes en cards del frontend** | Medio — UX visual del menu | Baja | F1 |
| F4 | **Tests modifiers + comandas** | Alto — 11 endpoints sin coverage | Media | Ninguno |
| F5 | **Duplicado detection** en import | Medio — re-importar crea duplicados | Baja | Ninguno |
| F6 | **Ordenamiento de categorias** | Bajo — hoy no se puede reordenar secciones | Baja | Ninguno |

### 2.2 Deuda tecnica

| Item | Riesgo | Accion |
|------|--------|--------|
| `imagen_url` es VARCHAR(500) sin pipeline de upload | No se pueden subir imagenes, solo pegar URL externa | Implementar F1 |
| `_bulk_create()` no detecta duplicados | Re-importar CSV crea items duplicados | Agregar check UNIQUE(tenant_id, nombre, categoria_id) |
| Modifier routes sin tests | Regresiones silenciosas | Implementar F4 |
| Comanda routes sin tests | FSM + precio computado sin validacion automatica | Implementar F4 |
| `import_from_ai()` no testeado end-to-end | Solo se testea el parser, no la llamada HTTP | Mock de httpx |

---

## 3. Plan de Desarrollo — Nuevas Features

### 3.1 FASE A: Google Cloud Storage + Upload de Imagenes

**Objetivo**: Que cada producto pueda tener una imagen almacenada en GCS.

#### Infraestructura GCS
```
Bucket: sudamerica-menu-images
Region: us-central1 (mismo que Cloud Run)
Acceso: Publico para lectura, authenticated para escritura
Estructura:
  {tenant_id}/productos/{producto_id}/original.webp
  {tenant_id}/productos/{producto_id}/thumb_400.webp
```

#### Backend — Nuevo service: `image_storage_svc.py`
```python
# Ubicacion: api_execute/app/services/image_storage_svc.py
# Dependencias: google-cloud-storage, Pillow

async def upload_product_image(
    tenant_id: UUID,
    producto_id: UUID,
    file_content: bytes,
    content_type: str,
) -> str:
    """
    1. Validar tipo (PNG, JPG, WebP) + tamano (max 5MB)
    2. Convertir a WebP con Pillow (reduce ~70% tamano)
    3. Generar thumbnail 400x400
    4. Upload original + thumb a GCS
    5. Retornar URL publica del original
    """

async def delete_product_image(tenant_id: UUID, producto_id: UUID) -> None:
    """Borrar original + thumbnail de GCS."""
```

#### Backend — Nuevo endpoint
```
POST   /api/v1/core/productos/{id}/imagen  (multipart/form-data, ADMIN)
DELETE /api/v1/core/productos/{id}/imagen  (ADMIN)
```

**Comportamiento**:
- POST sube imagen, la procesa, guarda en GCS, actualiza `producto.imagen_url`
- DELETE borra de GCS y setea `producto.imagen_url = null`
- Si ya existia una imagen, la reemplaza (borra anterior)

#### Config — Nuevas env vars
```
GCS_BUCKET_NAME=sudamerica-menu-images
GCS_PROJECT_ID=melodic-nature-484617-e6
# Service account con roles/storage.objectCreator + roles/storage.objectViewer
```

#### Frontend — Cambios
1. `ProductoForm.tsx`: Agregar dropzone de imagen (Mantine `<Dropzone>`)
2. `carta/page.tsx`: Mostrar thumbnail en ProductoCard y VariantGroupCard
3. Nuevo hook `useUploadProductImage.ts`

#### Dependencias nuevas
```
# backend/api_execute/requirements.txt
google-cloud-storage>=2.14.0
Pillow>=10.2.0
```

#### Consideraciones para NO romper nada
- `imagen_url` ya existe como campo — no hay migracion de schema
- El campo es nullable — productos sin imagen siguen funcionando
- El endpoint es ADICIONAL — no modifica endpoints existentes
- Frontend: las cards verifican `producto.imagen_url` antes de renderizar (graceful fallback)

#### Tests requeridos
```
test_upload_image_success          # Upload + verificar imagen_url actualizada
test_upload_image_invalid_type     # Rechaza .exe, .pdf, etc
test_upload_image_too_large        # Rechaza >5MB
test_upload_image_replaces_old     # Re-upload borra anterior
test_delete_image_success          # Borrar imagen + nullify campo
test_delete_image_nonexistent      # 404 si producto no tiene imagen
test_upload_requires_admin         # 403 sin rol ADMIN
```

---

### 3.2 FASE B: Import desde URL (Web Scraping)

**Objetivo**: El usuario pega la URL de su carta web y el sistema extrae automaticamente todos los productos con categorias e imagenes.

#### Problema tecnico: SPAs
La mayoria de sitios de restaurantes modernos son SPAs (React, Vue, Angular) o plataformas de delivery (Rappi, PedidosYa, UberEats). El HTML inicial no contiene el menu — se carga via JavaScript.

**Ejemplo real verificado**: `https://www.niusushi.cl/carta`
- HTML inicial: solo tracking scripts (GTM, Facebook Pixel)
- Menu: 19 categorias en tabs dinamicos, cada tab carga productos via JS
- Cada producto tiene: imagen, nombre, precio
- Sin JS render → 0 productos extraidos

#### Solucion: Browserless.io (servicio managed)

**Por que Browserless.io y no Puppeteer propio:**
| Criterio | Browserless.io | Puppeteer en Cloud Run |
|----------|---------------|----------------------|
| Setup | API key, 0 infra | Chromium en Docker (+400MB) |
| Mantenimiento | 0 | Updates de Chrome, memory leaks |
| Costo | Free tier 1000/mes, luego ~$0.01/render | Mas RAM en Cloud Run (~$5/mes) |
| Confiabilidad | 99.9% SLA | Depende de tu infra |
| Escalabilidad | Paralelo ilimitado | Limitado por instancias CR |

**Para el MVP**: Browserless.io. Si escala (>1000 imports/mes), migrar a Cloud Function con Puppeteer.

#### Flujo tecnico detallado

```
Usuario pega URL en frontend
         |
         v
POST /api/v1/core/menu/import-url
Body: { "url": "https://niusushi.cl/carta" }
         |
         v
┌── PASO 1: RENDER ──────────────────────────────────┐
│  web_scraper_svc.render_page(url)                  │
│  → Browserless.io API:                             │
│    1. Navega a URL                                 │
│    2. Espera network idle (2s)                     │
│    3. Detecta tabs/categorias en DOM               │
│    4. Si hay tabs → click en cada tab:             │
│       - Espera render                              │
│       - Screenshot de la seccion                   │
│       - Extrae image URLs del DOM                  │
│    5. Si no hay tabs → full-page screenshot        │
│  → Retorna: [screenshots], {image_map}             │
└────────────────────────────────────────────────────┘
         |
         v
┌── PASO 2: EXTRACT ─────────────────────────────────┐
│  menu_import_svc.import_from_screenshots(           │
│      screenshots, image_map)                        │
│  → Para cada screenshot:                            │
│    1. Enviar a Gemini Vision con _EXTRACT_PROMPT    │
│    2. Parsear JSON de items                         │
│  → Consolidar items de todos los tabs               │
│  → Fuzzy-match nombre_producto → image_url          │
│  → Retorna: [{nombre, precio, categoria,            │
│               descripcion, imagen_url_origen}, ...]│
└────────────────────────────────────────────────────┘
         |
         v
┌── PASO 3: IMAGES ──────────────────────────────────┐
│  image_storage_svc.batch_download_and_upload(       │
│      items_with_image_urls, tenant_id)              │
│  → Para cada item con imagen_url_origen:            │
│    1. Download imagen (httpx, timeout 10s)          │
│    2. Convertir a WebP                              │
│    3. Upload a GCS                                  │
│    4. Reemplazar imagen_url_origen → GCS URL        │
│  → Retorna: items con imagen_url = GCS              │
└────────────────────────────────────────────────────┘
         |
         v
┌── PASO 4: PERSIST ─────────────────────────────────┐
│  menu_import_svc._bulk_create(items, tenant_id)    │
│  → Reutiliza funcion existente                     │
│  → Crea categorias + productos                     │
│  → Ahora con imagen_url de GCS                     │
│  → Retorna: {created, categories_created, errors}  │
└────────────────────────────────────────────────────┘
```

#### Backend — Nuevo service: `web_scraper_svc.py`
```python
# Ubicacion: api_execute/app/services/web_scraper_svc.py
# Dependencias: httpx (ya existe)

BROWSERLESS_API = "https://chrome.browserless.io"

async def render_page(url: str, api_key: str) -> ScrapedPage:
    """
    Usa Browserless.io para:
    1. Render SPA completa
    2. Detectar tabs/secciones
    3. Navegar cada tab
    4. Screenshot + DOM de cada seccion
    5. Extraer image URLs

    Retorna ScrapedPage(screenshots=[], image_map={})
    """

async def _detect_menu_tabs(page_content: str) -> list[TabInfo]:
    """Detectar tabs/secciones clickeables en el DOM."""

async def _extract_image_urls(html: str) -> dict[str, str]:
    """Extraer mapa {alt_text: src_url} de todas las <img>."""
```

#### Backend — Nuevo endpoint
```
POST /api/v1/core/menu/import-url  (ADMIN)
Body: { "url": "https://niusushi.cl/carta" }
Response: {
    "created": 85,
    "categories_created": 19,
    "images_uploaded": 72,
    "errors": [],
    "source_url": "https://niusushi.cl/carta"
}
```

#### Config — Nuevas env vars
```
BROWSERLESS_API_KEY=<key>     # Solo en api-execute
BROWSERLESS_TIMEOUT=60        # Timeout para render (segundos)
```

#### Frontend — Cambios en MenuImportModal.tsx
```
MenuImportModal (actualizado)
├── Tab "Archivo": Dropzone CSV/PDF/imagen (existente, sin cambios)
└── Tab "URL": TextInput + boton "Importar desde web"
    ├── Validacion de URL (https://)
    ├── Loading state con progreso estimado (15-30s)
    ├── Preview de items extraidos antes de confirmar (NUEVO)
    └── Resultado: N platos, N categorias, N imagenes
```

#### Consideraciones para NO romper nada
- `menu_import.py` route NO se modifica — se agrega una NUEVA ruta `/import-url`
- `_bulk_create()` se reutiliza sin cambios (solo se le pasan items con `imagen_url`)
- `MenuImportModal` agrega un tab — el flujo de archivo existente no cambia
- Browserless.io es un servicio externo — si falla, no afecta nada mas
- El endpoint es asincrono (puede tardar 15-30s) — el frontend muestra loading

#### Manejo de sitios problematicos
```
1. SPA sin tabs (scroll infinito):
   → Full-page screenshot, Gemini procesa todo de una vez

2. SPA con tabs (como niusushi.cl):
   → Detectar tabs en DOM, click uno por uno, screenshot de cada tab

3. Sitio estatico (HTML plano):
   → Parse directo del HTML con BeautifulSoup, sin Browserless

4. Plataformas de delivery (Rappi, UberEats):
   → Screenshot approach (misma logica, diferente estructura)

5. Menu en PDF embebido:
   → Detectar <embed>/<iframe> con PDF, download, usar import_from_ai existente

6. Sitio con login/paywall:
   → Rechazar con error claro: "No se puede acceder al menu (requiere login)"

7. Sitio caido o URL invalida:
   → Timeout + error descriptivo
```

#### Tests requeridos
```
# Unit tests (mocking httpx + Browserless)
test_import_url_static_site           # HTML plano con productos
test_import_url_spa_with_tabs         # Verifica navegacion de tabs
test_import_url_downloads_images      # Verifica descarga + upload GCS
test_import_url_invalid_url           # Rechaza URL malformada
test_import_url_timeout               # Maneja timeout gracefully
test_import_url_no_menu_found         # Sitio sin menu detectable
test_import_url_deduplication         # No crea duplicados
test_import_url_requires_admin        # 403 sin ADMIN role
test_extract_image_urls_from_html     # Parser de <img> tags
test_fuzzy_match_product_to_image     # Matching nombre→imagen
test_batch_download_handles_failures  # Imagen caida no rompe todo
```

#### Estimacion de tiempo
| Tarea | Dias |
|-------|------|
| GCS setup + image_storage_svc | 1 |
| Endpoint upload imagen + frontend dropzone | 1 |
| web_scraper_svc (Browserless integration) | 2 |
| Endpoint import-url + AI extraction multi-tab | 1 |
| Frontend tab URL en MenuImportModal | 0.5 |
| Tests (unitarios con mocks) | 1.5 |
| **Total** | **~7 dias** |

---

### 3.3 FASE C: Inteligencia Avanzada (post-MVP)

| Feature | Descripcion | Cuando |
|---------|-------------|--------|
| Deteccion de modifiers desde web | Si el sitio tiene "Tamano: Regular/Grande", crear ModifierGroup automaticamente | Despues de Fase B |
| Deteccion de badges | NUEVO, POPULAR, SIN GLUTEN, VEGANO → tags en producto | Despues de Fase B |
| Preview antes de importar | Mostrar tabla editable con items extraidos antes de persistir | Despues de Fase B |
| Re-sync periodico | Cron que re-scrapea URL y detecta cambios (precios, items nuevos) | Fase 3 |
| Import desde Google Maps | Extraer menu desde ficha de Google My Business | Fase 3 |

---

## 4. Consideraciones Tecnicas Criticas

### 4.1 No romper lo que ya funciona

| Componente existente | Riesgo | Mitigacion |
|---------------------|--------|------------|
| `_bulk_create()` | Agregar campo imagen_url | El campo ya existe en Producto model, _bulk_create solo necesita `producto.imagen_url = item.get("imagen_url")` |
| `MenuImportModal` | Agregar tab URL | Tab es aditivo, no modifica el dropzone existente |
| `ProductoForm` | Agregar dropzone imagen | Campo adicional en el form, no afecta submit existente |
| `producto.imagen_url` | Era unused, ahora se usa | Campo nullable, productos sin imagen siguen OK |
| Endpoints existentes | No se modifican | Nuevas rutas son ADICIONALES (/import-url, /{id}/imagen) |
| comanda_svc pricing | No cambia | Imagenes no afectan logica de precios |
| AI orchestrator (catalogo en prompt) | No cambia | El catalogo en el prompt ya no incluye imagenes |

### 4.2 Dependencias nuevas y su impacto

| Dependencia | Para que | Tamano Docker | Riesgo |
|-------------|----------|--------------|--------|
| `google-cloud-storage` | Upload a GCS | ~5MB | Bajo (SDK oficial Google) |
| `Pillow` | Resize + WebP conversion | ~15MB | Bajo (standard, bien mantenido) |
| Browserless.io API | Render SPAs | 0 (servicio externo) | Medio (dependencia externa) |

**Impacto en Docker**: +20MB en imagen de api-execute (de ~250MB a ~270MB). Aceptable.

### 4.3 Migraciones de base de datos

**NO se requieren migraciones**. Todos los campos necesarios ya existen:
- `productos.imagen_url` — VARCHAR(500), ya existe, nullable
- No hay tablas nuevas
- No hay columnas nuevas

### 4.4 Seguridad

| Preocupacion | Mitigacion |
|-------------|------------|
| SSRF via URL import | Validar URL: solo HTTPS, no IPs privadas (10.x, 192.168.x, 127.x) |
| Image bombs (decompression) | Pillow con limits: max 10MP, max 10MB raw |
| GCS permissions | Service account con SOLO `storage.objects.create` + `storage.objects.delete` en bucket especifico |
| Browserless abuse | Rate limit: max 5 imports/tenant/hora |
| Malicious URLs | Timeout 60s, no seguir redirects infinitos |

### 4.5 Performance

| Operacion | Tiempo esperado | Mitigacion |
|-----------|----------------|------------|
| Upload imagen individual | <2s | Async, no bloquea UI |
| Import CSV | <1s | Ya funciona rapido |
| Import PDF/imagen | 5-15s | Ya funciona, Gemini Vision |
| Import desde URL (sitio simple) | 10-20s | Loading state en frontend |
| Import desde URL (sitio con tabs) | 20-45s | Progress bar + tabs procesados/total |
| Batch download imagenes | 5-30s (depende de # imagenes) | Paralelo con asyncio.gather, max 10 concurrent |

---

## 5. SQL — Referencia rapida

### Tablas base (001_schema.sql)
```sql
-- categorias
CREATE TABLE categorias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, nombre)
);

-- productos
CREATE TABLE productos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    categoria_id UUID REFERENCES categorias(id),
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    precio NUMERIC(12,2) NOT NULL CHECK (precio >= 0),
    sku VARCHAR(100),
    imagen_url VARCHAR(500),
    stock INT DEFAULT 0 CHECK (stock >= 0),
    disponible BOOLEAN DEFAULT true,
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, id)
);
```

### Tablas Resto Fase 1 (sql/005_resto_fase1.sql)
```sql
-- modifier_groups, modifiers, producto_modifier_groups
-- comandas, comanda_items
-- Ver archivo completo en backend/infra/sql/005_resto_fase1.sql
```

### Queries utiles (Cloud SQL prod)
```sql
-- Productos por tenant
SELECT p.nombre, p.precio, c.nombre as categoria
FROM productos p
LEFT JOIN categorias c ON p.categoria_id = c.id
WHERE p.tenant_id = '<tenant_id>' AND p.activo = true
ORDER BY c.nombre, p.nombre;

-- Modifier groups con sus opciones
SELECT mg.nombre as grupo, mg.tipo, m.nombre as opcion, m.precio_delta
FROM modifier_groups mg
JOIN modifiers m ON m.grupo_id = mg.id
WHERE mg.tenant_id = '<tenant_id>' AND mg.activo = true AND m.activo = true
ORDER BY mg.nombre, m.orden;

-- Comandas activas (KDS)
SELECT c.id, c.estado, c.tipo_entrega, c.numero_mesa,
       ci.cantidad, p.nombre as producto, ci.modifiers_json
FROM comandas c
JOIN comanda_items ci ON ci.comanda_id = c.id
JOIN productos p ON ci.producto_id = p.id
WHERE c.tenant_id = '<tenant_id>'
  AND c.activo = true
  AND c.estado IN ('PENDIENTE', 'EN_COCINA', 'LISTO')
ORDER BY c.prioridad DESC, c.created_at ASC;
```

---

## 6. Changelog

### 2026-03-13 — Sudamérica AI Resto Fase 1 (commit 2dafa08)
- Creados modelos: ModifierGroup, Modifier, ProductoModifierGroup, Comanda, ComandaItem
- Creados endpoints: modifiers (11), comandas (6), menu/import (1)
- Creados servicios: modifier_svc, comanda_svc, menu_import_svc, fidelizacion_svc
- Frontend: pagina /carta con tabs Platos + Modificadores
- Frontend: MenuImportModal, ModifierEditor, ProductoForm
- SQL: 005_resto_fase1.sql (tablas + indices + RLS)
- Tests: test_menu_import (11), test_comanda_notify (4), test_fidelizacion (4)

### 2026-03-14 — Fix modifier column name (commit 2dafa08)
- Fix: `m.modifier_group_id` → `m.grupo_id` en query de catalogo
- Fix: try/except en carga de modifiers para tablas faltantes

### 2026-03-14 — Documentacion (este archivo)
- Creada bitacora completa del modulo
- Documentado plan de desarrollo: GCS + URL import + inteligencia avanzada
- Identificados gaps de testing: modifiers + comandas sin coverage

### 2026-03-14 — Implementacion Fase A + B (GCS + URL Import)

**Backend — Archivos nuevos**:
- `api_execute/app/services/image_storage_svc.py` (178 lineas) — Upload/delete/download de imagenes GCS, conversion WebP, thumbnails, batch download
- `api_execute/app/services/web_scraper_svc.py` (186 lineas) — Browserless.io scraper, SSRF protection, image URL extraction, fuzzy matching
- `api_execute/tests/test_image_storage.py` (181 lineas, 24 tests) — URL validation, image extraction, fuzzy match, upload validation
- `api_execute/tests/test_web_scraper.py` (127 lineas, 5 tests) — URL import flow E2E con mocks

**Backend — Archivos modificados**:
- `api_execute/app/config.py` — +4 env vars: GCS_BUCKET_NAME, GCS_PROJECT_ID, BROWSERLESS_API_KEY, BROWSERLESS_TIMEOUT
- `api_execute/app/services/menu_import_svc.py` — Nueva funcion `import_from_url()` (120 lineas), `_bulk_create` ahora incluye `imagen_url`
- `api_execute/app/routes/menu_import.py` — Nuevo endpoint `POST /import-url`
- `api_execute/app/routes/productos.py` — Nuevos endpoints `POST /{id}/imagen` y `DELETE /{id}/imagen`
- `api_execute/requirements.txt` — +google-cloud-storage, +Pillow
- `api_execute/app/models/lead.py` — Fix: `ARRAY(String)` → `JSON` (SQLite compat para tests)
- `api_execute/app/models/comanda.py` — Fix: `JSONB` → `JSON` (SQLite compat para tests)

**Frontend — Archivos nuevos**:
- `hooks/useUploadProductImage.ts` (138 lineas) — Upload/delete image hooks
- `hooks/useMenuImportUrl.ts` (71 lineas) — URL import hook

**Frontend — Archivos modificados**:
- `lib/types.ts` — Agregado `imagen_url: string | null` a interfaz Producto
- `components/carta/MenuImportModal.tsx` — Tabs "Archivo" + "Desde URL" con TextInput
- `app/(dashboard)/carta/page.tsx` — ProductoCard muestra thumbnail (56x56), VariantGroupCard muestra mini-thumb (28x28)

**Tests**: 119/119 pasando (85 existentes + 29 nuevos + 5 pre-existentes que ahora corren gracias a fix SQLite compat)

**Endpoints nuevos**:
| Metodo | Path | Auth | Funcion |
|--------|------|------|---------|
| POST | `/api/v1/core/menu/import-url` | ADMIN | Import menu desde URL web |
| POST | `/api/v1/core/productos/{id}/imagen` | ADMIN | Upload imagen producto → GCS |
| DELETE | `/api/v1/core/productos/{id}/imagen` | ADMIN | Borrar imagen de GCS |

**Pendiente para activar en produccion**:
1. Crear bucket GCS `sudamerica-menu-images` en `melodic-nature-484617-e6`
2. Configurar env vars en Cloud Run: `GCS_BUCKET_NAME`, `BROWSERLESS_API_KEY`
3. Service account necesita `roles/storage.objectAdmin` en el bucket
4. `pip install google-cloud-storage Pillow` ya esta en requirements.txt (Docker lo instala)
