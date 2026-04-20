# Estructura interna del frontend

Organización del código fuente del frontend por tipo y responsabilidad.

---

## Directorio `app/`

Rutas y layouts de la aplicación (Next.js App Router):

| Ruta | Archivo | Descripción |
|---|---|---|
| `/` | `page.tsx` | Login |
| `/chat` | `chat/page.tsx` | Workspace del asistente |
| `/admin/manuals` | `admin/manuals/page.tsx` | Consola administrativa |
| `/settings` | `settings/page.tsx` | Configuración de perfil |

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
| `chat/` | Panel de conversación e historial |
| `admin/` | Gestión de manuales |
| `settings/` | Configuración de perfil y contraseña |

Cada módulo exporta sus componentes públicos mediante un barrel file (`index.ts`).

## Directorio `lib/`

Clientes HTTP (`api-client.ts`), helpers de autenticación (`auth.ts`), perfil (`profile.ts`), manuales (`manuals.ts`) y utilidades (`cn.ts`).

## Directorio `styles/`

Tokens de diseño (Tailwind CSS v4 `@theme` block) y estilos base. El tema oscuro se define mediante variables CSS: `--color-bg`, `--color-surface`, `--color-ink`, `--color-accent`, etc.
