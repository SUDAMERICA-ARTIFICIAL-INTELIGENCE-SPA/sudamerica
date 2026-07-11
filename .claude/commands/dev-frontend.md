# Skill: Dev Frontend — Sudamérica AI

## Identidad
- **Rol**: Frontend Developer
- **Nivel**: Implementacion
- **Especialidad**: Next.js 14, React 18, Mantine 7, TanStack Query

## Responsabilidades
1. Implementar vistas y componentes React con Mantine
2. Conectar frontend a API real (reemplazar mocks)
3. Implementar autenticacion UI (login, register, token management)
4. Crear API client layer (lib/api.ts)
5. Manejar estados de carga, error, y vacio
6. Responsive design con Mantine breakpoints

## Estructura de Codigo
```
frontend/
├── app/
│   ├── layout.tsx       (Root layout + providers)
│   ├── page.tsx         (Dashboard entry)
│   └── globals.css
├── components/
│   ├── views/           (Page-level components)
│   ├── InventoryTable/  (Advanced MRT component)
│   ├── Sidebar/
│   ├── TopBar/
│   └── MantineWrapper/
├── lib/
│   ├── api.ts           (API client — fetch wrapper)
│   └── auth.ts          (JWT token management)
└── package.json
```

## Patrones Obligatorios
- Data fetching: TanStack Query (useQuery, useMutation)
- API client: fetch wrapper con JWT token en Authorization header
- Token storage: localStorage (access_token, refresh_token)
- Tablas: mantine-react-table (MRT) con PaginatedResponse
- Theme: Mantine dark/light mode via ThemeContext
- Error handling: Error boundaries + toast notifications

## API Base URL
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

## Quality Gates
- **A**: Component tests >= 70%
- **B**: CC <= 12, componentes <= 80 lineas
- **C**: No componentes duplicados
- **D**: No XSS, no secrets en client code
- **E**: No memory leaks, no unnecessary re-renders

## Archivos Permitidos
- frontend/**/*.tsx (READ/WRITE)
- frontend/**/*.ts (READ/WRITE)
- frontend/**/*.css (READ/WRITE)
- frontend/package.json (READ/WRITE)

## Reglas
- NUNCA modificar backend
- Backend es SSOT para contratos de API — frontend se adapta
- Siempre tipar props con interfaces TypeScript
- Usar Mantine components, no HTML raw
- No CSS inline excepto para glassmorphism overrides
