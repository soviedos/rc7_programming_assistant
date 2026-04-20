# Estructura interna del frontend

Organización del código fuente del frontend por tipo y responsabilidad.

---

## Directorio `app/`

Rutas y layouts de la aplicación (Next.js App Router):

| Ruta | Archivo | Descripción |
|---|---|---|
| `/` | `page.tsx` | Landing / Login |
| `/app` | `app/page.tsx` | Workspace del asistente |
| `/admin` | `admin/page.tsx` | Consola administrativa |

## Directorio `components/`

Componentes reutilizables y presentacionales, separados de `features/` para no mezclar piezas visuales con lógica de negocio.

| Subdirectorio | Contenido |
|---|---|
| `auth/` | Formulario de login, rutas protegidas |
| `chat/` | Componentes de conversación |
| `layout/` | Shell de la aplicación, header, perfil de sesión |
| `shared/` | Componentes genéricos reutilizables |

## Directorio `features/`

Módulos funcionales del producto, agrupados por dominio:

| Módulo | Responsabilidad |
|---|---|
| `auth/` | Lógica de autenticación |
| `history/` | Historial de consultas |
| `workspace/` | Panel principal del asistente |
| `references/` | Referencias documentales |
| `robots/` | Configuración del robot |
| `admin/` | Funcionalidades administrativas |

## Directorio `lib/`

Clientes HTTP, helpers de formateo, manejo de tokens y utilidades transversales del cliente.

## Directorio `styles/`

Estilos globales y tokens de diseño visual.

## Directorio `types/`

Tipos TypeScript compartidos por toda la aplicación web.
