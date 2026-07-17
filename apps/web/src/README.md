# Estructura interna del frontend

Organización del código fuente del frontend por tipo y responsabilidad.

---

## Directorio `app/`

Rutas y layouts de la aplicación (Next.js App Router):

| Ruta | Archivo | Descripción |
|---|---|---|
| `/` | `page.tsx` | Login |
| `/chat` | `chat/page.tsx` | Workspace del asistente (3 columnas) |
| `/settings` | `settings/page.tsx` | Configuración de perfil |
| `/profile` | `profile/page.tsx` | Redirect a `/settings` |
| `/admin` | `admin/page.tsx` | Redirect a `/admin/manuals` |
| `/admin/manuals` | `admin/manuals/page.tsx` | Consola admin: base documental |
| `/admin/users` | `admin/users/page.tsx` | Consola admin: usuarios |
| `/admin/roles` | `admin/roles/page.tsx` | Consola admin: permisos por rol |
| `/admin/settings` | `admin/settings/page.tsx` | Consola admin: parámetros del pipeline |
| `/admin/audit` | `admin/audit/page.tsx` | Consola admin: registro de eventos |
| `/api/v1/*` | `api/v1/[...path]/route.ts` | Route handler: proxy a la API (no es una página) |

## Directorio `components/`

Componentes compartidos y presentacionales:

| Subdirectorio | Contenido |
|---|---|
| `layout/` | Header de la aplicación |
| `shared/` | Componentes genéricos (robot SVG, etc.) |

## Directorio `features/`

Módulos funcionales del producto, agrupados por dominio:

| Módulo | Responsabilidad |
|---|---|
| `auth/` | Login, sesión, rutas protegidas, menú de usuario |
| `chat/` | Configuración del robot, canvas de código PAC, conversación con streaming SSE e historial |
| `admin/` | Manuales, usuarios, roles, settings, registro de auditoría y navegación admin |
| `settings/` | Configuración de perfil y contraseña |

Cada módulo exporta sus componentes públicos mediante un barrel file (`index.ts`).

## Directorio `lib/`

Cliente HTTP base (`api-client.ts`) y los clientes por dominio: autenticación (`auth.ts`),
perfil (`profile.ts`), manuales (`manuals.ts`), chat (`chat.ts`), roles (`roles.ts`) y la
consola admin (`admin-users.ts`, `admin-settings.ts`, `admin-audit.ts`). Utilidades en
`utils.ts` (incluido `cn`) y `ui.ts`.

## Directorio `styles/`

Tokens de diseño (Tailwind CSS v4 `@theme` block) y estilos base. El tema oscuro se define mediante variables CSS: `--color-bg`, `--color-surface`, `--color-ink`, `--color-accent`, etc.
