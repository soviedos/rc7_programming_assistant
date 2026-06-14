# Web — Frontend Next.js

Aplicación frontend del RC7 Programming Assistant: login, workspace del asistente PAC con
streaming SSE, y consola de administración.

---

## Stack técnico

| Tecnología | Versión | Uso |
|---|---|---|
| Next.js | `16.2.4` (App Router, `output: "standalone"`) | Framework React + proxy de API |
| React / React DOM | `19.2.5` | UI |
| TypeScript | `^6` | Tipado estático |
| Tailwind CSS | `^4` (+ `@tailwindcss/postcss`) | Estilos |
| lucide-react, clsx, class-variance-authority, tailwind-merge | — | UI utilities |
| Vitest + Testing Library + jsdom | — | Testing |

---

## Estructura

```text
apps/web/src/
├── app/                      # App Router (rutas + layouts)
│   ├── page.tsx              # Login / landing
│   ├── chat/                 # Workspace del asistente (SSE)
│   ├── profile/  settings/   # Perfil y preferencias del usuario
│   ├── admin/                # Consola admin: page + users, manuals, settings, audit, roles
│   └── api/v1/[...path]/route.ts  # Proxy catch-all → FastAPI (reenvía cookie)
├── features/                 # Lógica por dominio: auth, chat, admin, settings
├── components/               # layout/ y shared/ (UI reutilizable)
├── lib/                      # api-client + clientes por dominio (auth, chat, manuals, …)
└── styles/globals.css        # Tailwind
```

**Punto de entrada:** `src/app/layout.tsx` (root layout) + `src/app/page.tsx`.

**Proxy de API:** [`src/app/api/v1/[...path]/route.ts`](src/app/api/v1/[...path]/route.ts) reenvía
todos los `/api/v1/*` a `INTERNAL_API_URL` propagando la cookie de sesión. Detecta
`text/event-stream` y hace passthrough del stream SSE sin buffering; preserva binarios (PDF) con
`arrayBuffer`; reenvía `Set-Cookie` y `Content-Disposition`. `maxDuration = 300` (SSE).

**Cliente HTTP:** [`src/lib/api-client.ts`](src/lib/api-client.ts) — `fetch` con `credentials: "include"`,
normaliza errores `{detail}` (string o lista de validación Pydantic) y expone `api.get/getMaybe/post/put/deleteVoid/postFormData`.

---

## Funcionalidades implementadas

- Login con validación amigable y manejo de errores; sesión por cookie HttpOnly.
- Navegación protegida por sesión y rol activo; cambio de rol.
- Workspace del asistente: envía `ChatRequest`, consume **SSE** (`chunk` → `done`/`error`), muestra
  `summary` + `pac_code` en el canvas + referencias.
- Consola admin: usuarios (CRUD), manuales (carga PDF + extracción de metadatos, estado de ingestión,
  reintentar/cancelar), permisos de rol, settings (edición en caliente), audit log (filtros/paginación).
- Perfil: edición de nombre/preferencias y cambio de contraseña.

> **Pendiente:** login con Google SSO (el backend expone `/auth/providers` con la nota, pero no está implementado).

---

## Variables de entorno

| Variable | Default | Uso |
|---|---|---|
| `INTERNAL_API_URL` | `http://api:8000` | Destino del proxy server-side hacia FastAPI |
| `NEXT_PUBLIC_API_BASE_URL` | `""` (vacío) | Base de las llamadas client-side; vacío = usa el proxy de Next.js |
| `NEXT_ALLOWED_DEV_ORIGINS` | — | Hosts extra permitidos para el WebSocket HMR de `next dev` (CSV) |

---

## Ejecución y pruebas

En el stack Docker el servicio `web` corre el build **standalone** de producción (`node server.js`);
no monta el código fuente (ver [infra/docker/README.md](../../infra/docker/README.md)).

```bash
docker compose exec web npm test      # Vitest (suite del frontend)
npm run dev                           # desarrollo local con hot-reload (fuera de Docker)
```
