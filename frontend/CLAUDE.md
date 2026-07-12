# Sudamérica AI CRM — Project Rules

> Claude Code: lee este archivo completo al inicio de cada sesión.
> Reglas detalladas por dominio en `.claude/rules/`. Skills en `.claude/skills/`.

## Stack

- **Frontend:** Next.js 15 (App Router) + React 19 + TypeScript strict
- **UI:** Mantine 7 — NUNCA Tailwind. NUNCA HTML puro si existe componente Mantine
- **State:** TanStack Query v5 (server), Zustand (client)
- **Charts:** Recharts (lines/bars/areas) + ApexCharts (heatmaps/gauges/funnels)
- **Animations:** Framer Motion (counters, transitions, micro-interactions)
- **Linter/Formatter:** Biome (NO ESLint/Prettier) — `biome.json` único
- **Types:** `strict: true` + `@total-typescript/ts-reset` + Zod schemas
- **Tests:** Vitest (unit/integration) + Playwright (E2E)
- **Package Manager:** pnpm
- **Icons:** @tabler/icons-react
- **Backend:** 5 FastAPI microservices — api_execute(:8000), callback_manual(:8002), tasks(:8003), canales_service(:8004), open_agent(:8005)
- **Auth:** JWT Bearer — localStorage (access_token + refresh_token)
- **Multi-tenant:** Todas las API calls usan `tenant_id` del JWT

## Commands

```bash
pnpm dev              # Dev server (turbopack)
pnpm build            # Production build
pnpm typecheck        # tsc --noEmit
pnpm lint             # biome check .
pnpm lint:fix         # biome check --write .
pnpm test             # vitest run
pnpm test:watch       # vitest
pnpm test:e2e         # playwright test
```

## MCP Servers (pre-configurados en .mcp.json)

```bash
claude mcp add postgres -- npx -y @modelcontextprotocol/server-postgres "postgresql://user:pass@localhost:5432/crm_db"
claude mcp add context7 -- npx -y @upstash/context7-mcp@latest
claude mcp add github -- npx -y @modelcontextprotocol/server-github
claude mcp add vercel -t http https://mcp.vercel.com/
claude mcp add stripe -t http https://mcp.stripe.com
claude mcp add figma -t http https://mcp.figma.com/mcp
```

## Quality Gates (NON-NEGOTIABLE)

1. **TypeScript:** Zero `any`. Usar `unknown` + type guards. Todos los API responses tipados con Zod
2. **Performance:** Lighthouse ≥90, FCP <1.5s, CLS <0.1. Lazy-load charts con `next/dynamic`
3. **Accessibility:** `aria-label` en todo elemento interactivo. Contraste ≥4.5:1. IDs únicos
4. **Testing:** Tests unitarios para funciones de cálculo (KPIs). Component tests para flujos críticos
5. **Format:** Biome se ejecuta automáticamente vía hook PostToolUse. NO formatear manualmente

## Prohibiciones Absolutas

- ❌ NUNCA usar Tailwind CSS ni clases de utilidad
- ❌ NUNCA usar `any` en TypeScript
- ❌ NUNCA ejecutar `git checkout .` ni `git reset --hard` (usar `/rewind` en su lugar)
- ❌ NUNCA modificar `.env`, `.env.local`, ni archivos en `.claude/`
- ❌ NUNCA instalar dependencias sin aprobación (`askUser` en settings)
- ❌ NUNCA dejar componentes sin skeleton loaders durante la carga

---

## Folder Structure

```
frontend_final/
├── CLAUDE.md                      # ESTE ARCHIVO — reglas globales (<200 líneas)
├── .claude/
│   ├── settings.json              # Hooks, permisos, tool search
│   ├── rules/
│   │   ├── components.md          # Reglas para *.tsx en components/
│   │   ├── hooks.md               # Reglas para hooks/
│   │   ├── charts.md              # Reglas para charts/
│   │   └── api-layer.md           # Reglas para lib/ y stores/
│   └── skills/
│       ├── mantine-conventions/SKILL.md
│       ├── dashboard-kpis/SKILL.md
│       └── sector-config/SKILL.md
├── app/
│   ├── layout.tsx                 # MantineProvider + QueryClientProvider + fonts
│   ├── page.tsx                   # Redirect → /dashboard
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── onboarding/page.tsx    # Wizard de configuración inicial
│   └── (dashboard)/
│       ├── layout.tsx             # Sidebar + TopBar + AlertCenter
│       ├── dashboard/page.tsx     # Executive Summary (Z-pattern)
│       ├── pipeline/page.tsx      # Kanban board
│       ├── leads/page.tsx         # Table + detail drawer
│       ├── productos/page.tsx
│       ├── ventas/page.tsx
│       ├── ia/page.tsx            # AI Performance (F-pattern)
│       ├── reportes/page.tsx      # Tabs: Diario/Semanal/Mensual
│       ├── equipo/page.tsx        # Leaderboard + targets
│       ├── configuracion/page.tsx # Tenant config + AI agent setup
│       └── roi/page.tsx           # ROI calculator ("Recibo de Valor")
├── components/
│   ├── ui/                        # Atomic: KpiCard, ScoreThermometer, AlertBadge
│   ├── charts/                    # Lazy-loaded chart wrappers
│   ├── dashboard/                 # ExecutiveSummary widgets
│   ├── pipeline/                  # KanbanBoard, LeadCard, DragColumn
│   ├── leads/                     # LeadDetail, LeadForm, LeadFilters
│   ├── ia/                        # AIMetrics, ConversationViewer, InsightsFeed
│   ├── reportes/                  # ReportCard, FunnelChart, HeatmapWeek
│   └── layout/                    # Sidebar, TopBar, CommandPalette, AlertCenter
├── hooks/                         # Un hook por entidad — ver Data Model
├── lib/
│   ├── api.ts                     # Fetch wrapper: JWT, timeout, error handling
│   ├── auth.tsx                   # AuthContext + useAuth + route guards
│   ├── types.ts                   # ALL interfaces (ver sección Data Model)
│   ├── enums.ts                   # Frontend enum mirrors
│   ├── kpi-formulas.ts            # Pure functions — TODAS las fórmulas de KPI
│   ├── chart-config.ts            # Shared palette, theme, tooltip styles
│   └── sector-config.ts           # Map<sector, {fields, kpis, benchmarks}>
├── stores/
│   └── ui-store.ts                # Zustand: sidebar, theme, active filters
├── biome.json
├── tsconfig.json
└── .mcp.json
```

---

## .claude/settings.json

```json
{
  "permissions": {
    "allow": ["Read", "Write", "Glob", "Grep", "Bash(pnpm:*)", "Bash(npx:*)"],
    "deny": ["Bash(rm -rf:*)", "Bash(git reset:*)", "Bash(git checkout .:*)"],
    "askUser": ["Bash(pnpm add:*)", "Bash(git push:*)", "Bash(git commit:*)"]
  },
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{"type": "command", "command": "npx @biomejs/biome check --write --changed"}]
    }],
    "Stop": [{
      "hooks": [{"type": "command", "command": "pnpm typecheck && pnpm test"}]
    }]
  },
  "env": {
    "ENABLE_TOOL_SEARCH": "auto"
  }
}
```

---

## Design System

### Regla de los 6 Segundos
El usuario (dueño de PYME LATAM, no técnico, poco tiempo) debe entender el estado del negocio en 6 segundos. Cada componente responde: "¿Qué debo hacer AHORA?"

### Palette
```
--bg-primary: #F9FAFB       --accent-primary: #4C6EF5 (indigo)
--bg-card: #FFFFFF           --accent-secondary: #FF6B35 (orange CTA)
--bg-dark: #1A1B1E           --accent-gold: #F59F00 (AI contributions)
--text-primary: #212529      --success: #37B24D
--text-secondary: #868E96    --warning: #F08C00
                             --danger: #E03131
```

### Typography
Inter (Google Fonts) — 400/500/600/700. Big numbers: 32-40px bold. Body: 14px. Labels: 12px uppercase.

### Components
- Cards: `border-radius: 12px`, `shadow: 0 1px 3px rgba(0,0,0,0.08)`
- Spacing: 8px grid. Transitions: 200ms ease-out
- Skeleton loaders en TODOS los componentes que cargan datos
- Toast notifications en TODAS las mutaciones

---

## Lead FSM

```
NUEVO → CONTACTADO → EN_PROCESO → CONVERTIDO | DESCARTADO
```

Frontend desactiva transiciones imposibles. Backend las valida.

### Enums
```
LeadEstado: NUEVO | CONTACTADO | EN_PROCESO | CONVERTIDO | DESCARTADO
LeadCanal: WHATSAPP | INSTAGRAM | FACEBOOK | WEB | TELEFONO | EMAIL | REFERIDO
UserRole: ADMIN | ASESOR | VIEWER
TenantPlan: FREE | PRO
RevisionAccion: APROBAR | EDITAR | RECHAZAR
SubAgenteType: RAG | COTIZADOR | SEGUIMIENTO | FAQ
```

### Plans
| Feature | FREE | PRO |
|---|---|---|
| Max users | 3 | 15 |
| Max leads/mes | 100 | Ilimitado |
| AI Agent | Básico | Full sub-agents |
| Reports | Básicos | Avanzados + Export |
| Dashboard | Solo resumen | Todas las vistas |

### API Conventions
- PATCH para updates. Soft-delete via `activo` boolean
- Confidence ≥ 0.85 → auto-send. < 0.85 → human review
- Pagination: `?page=1&page_size=20`
- `Venta.total` es INMUTABLE (server-computed)

---

## Data Model

> Todas las interfaces están en `lib/types.ts`. Aquí solo el índice.

### Existentes (13 tablas)
`Tenant`, `Usuario`, `Lead`, `Producto`, `Categoria`, `Venta`, `AgenteConfig`, `AIConversation`, `AIEmbedding`, `RevisionHumana`, `StripeEvent`, `TaskLog`

### Nuevas (10 tablas — backend en desarrollo)
`LeadStageHistory`, `LeadInteraction`, `MarketingCampaign`, `CustomerFeedback`, `SalesTarget`, `CalendarEvent`, `QuoteEstimate`, `TenantEconomicsSnapshot`, `SmartAlert`, `UserActivityLog`

### Hooks (1 por entidad)
`useLeads`, `useProductos`, `useVentas`, `useCategorias`, `useUsuarios`, `useMetricas`, `useAIConversations`, `useRevisionHumana`, `useLeadStageHistory`, `useLeadInteractions`, `useSalesTargets`, `useCalendarEvents`, `useQuotes`, `useSmartAlerts`, `useMarketingCampaigns`, `useCustomerFeedback`, `useTenantEconomics`, `useUserActivity`

---

## Dashboard Views

### VIEW 1: Executive Summary (`/dashboard`) — Z-Pattern
**Row 1:** 5 KPI Cards (Ventas vs Meta, Nuevos Leads, Conversión %, IA Atendidas, Ahorro IA $)
**Row 2:** Revenue Real vs Forecast chart (2/3) + Smart Alerts feed (1/3)
**Row 3:** "Requiere tu atención" — AI-generated Next Best Actions table

### VIEW 2: Pipeline (`/pipeline`) — Kanban
Columnas: NUEVO → CONTACTADO → EN_PROCESO → CONVERTIDO | DESCARTADO
Card: nombre (bold) + valor ($) + aging badge + canal icon + AI Score (❄️🟡🔥)
Header columna: suma total ($). Filtros: asesor, canal, score, sector

### VIEW 3: AI Performance (`/ia`) — F-Pattern
Top: Auto-resolución %, Costo/Conversación, Horas Ahorradas (animated), ROI IA
Middle: Donut (Humano vs IA) + Barras (horas/semana)
Bottom: "Victorias de la IA" — log de leads rescatados de noche/fin de semana

### VIEW 4: Reports (`/reportes`) — Tabs
Diario (actividad), Semanal (pipeline health), Mensual (finanzas + ROI)
Pre-built: Sales Velocity, Win/Loss, Channel ROI, Acquisition Funnel

---

## KPI Formulas (in `lib/kpi-formulas.ts`)

### Pipeline
- Pipeline Velocity = (Opps × AvgDeal × WinRate) / AvgCycleDays
- Win Rate = Won / (Won + Lost) × 100
- Pipeline Coverage = Open Pipeline / Quota
- Forecast Accuracy = Actual / Forecast × 100

### AI Efficiency
- Auto-resolution = AI_resolved_no_human / Total_AI × 100
- Cost/Conversation = Total_Token_Cost / Total_Conversations
- Hours Saved = AI_resolved × 0.75h
- AI ROI = (Revenue_AI_leads - AI_cost) / AI_cost × 100

### Client & Retention
- CAC = Marketing_Spend / New_Customers
- LTV = (ARPU × Margin) / Churn_Rate
- LTV:CAC target: > 3:1. NPS = %Promoters - %Detractors

### Operational
- Lead Response Time = Σ(first_response - created) / count
- Workload = active_leads per advisor

---

## Sector Config (`lib/sector-config.ts`)

| Sector | Primary KPI | LATAM Benchmark |
|---|---|---|
| Salud/Estética | Tasa No-Show | FCR 75-85%, <48h ciclo |
| Inmobiliario | Días hasta Cierre | 60-120 días, retención alquiler 70-80% |
| Automotriz | Test-Drive Conversion | 20-35% test-drive rate |
| Gastronomía | Recurrencia de Compra | 30-45% recurrencia 30d |
| Educación | Enrollment Velocity | 40-55% asistencia webinar |
| Mascotas | Predictive Restock | >25% predicción reposición |
| Retail | Carritos Recuperados IA | 15-25% recovery, WA >12% conv |
| B2B | Win Rate Propuestas | 20-35% win rate |
| Turismo | Booking Lead Time | WA ROI hasta 16x vs OTAs |

### LATAM Rules
- WhatsApp = canal #1 (>90% penetración comercial)
- Días 25-31 del mes = días de pago → +40% conversión
- CPC Meta Ads LATAM: ~$0.19 USD (83% menor que global)
- 70% transacciones son móviles — pagos in-chat (Mercado Pago, Tukuy)

---

## Smart Alerts

| Type | Trigger | UI |
|---|---|---|
| `hot_lead` | Score ≥85 | 🔥 Red badge, top Kanban |
| `stalled_deal` | 0 activity >5 days | ⏳ Yellow, days count |
| `churn_risk` | Sentiment declining | 📉 Red card background |
| `anomaly_detected` | Activity drop >30% WoW | ⚠️ Dashboard banner |
| `no_show_risk` | History of no-shows | 🚫 Calendar warning |

---

## ROI Calculator (`/roi`)

1. **Tiempo Ahorrado** = AI_resolved × 0.75h × hourly_rate
2. **Ventas Incrementales** = Revenue de leads atendidos fuera de horario por IA
3. **Eficiencia** = ((LRT_historical - LRT_current) / LRT_historical) × 100
4. **ROI Global** = ((Revenue_incremental + Cost_savings) - SaaS_price) / SaaS_price × 100

Visual: animated "receipt" widget con Framer Motion counters.

---

## Visualization Guide

| Type | Library | Use Case |
|---|---|---|
| Line/Bar/Area | Recharts | Revenue, pipeline, time series |
| Heatmap | ApexCharts | Hour/day activity optimization |
| Funnel | ApexCharts/Nivo | Pipeline conversion |
| Gauge | ApexCharts | Goal progress |
| Donut | Recharts | Distribution (channel, human vs AI) |
| Animated counter | Framer Motion | Big numbers (savings, revenue) |
| Kanban | Custom + Mantine DnD | Pipeline view |
| Sparklines | Recharts mini | KPI card trends |

---

## Implementation Phases

### Phase 1 — Core (Week 1-2)
Auth, layout shell, Dashboard Summary, Leads CRUD, Products, Sales, API layer

### Phase 2 — Pipeline & AI (Week 3-4)
Kanban, AI Performance, Human Review, Smart Alerts, Basic Reports

### Phase 3 — Analytics (Week 5-6)
KPI engine, ROI Calculator, Sector fields, Gamification, Insights feed, Heatmaps

### Phase 4 — Polish (Week 7)
Dark mode, Onboarding wizard, Cmd+K palette, Mobile responsive, Code splitting
