# Frontend

Documentación de la interfaz web del RC7 Programming Assistant.

---

## Contenido

| Documento | Descripción |
|---|---|
| [workspace-layout.md](./workspace-layout.md) | Diseño del workspace principal del asistente |

## Filosofía de diseño

La interfaz se comporta como una **herramienta de ingeniería asistida**, no como un chat genérico. El diseño separa el acceso, el trabajo operativo y la administración bajo una identidad visual consistente.

---

## Rutas implementadas

### `/` — Login

- Diseño profesional con identidad RobLab · Universidad CENFOTEC
- Robot SVG decorativo en el lado izquierdo
- Autenticación con correo autorizado y contraseña
- Validación amigable con mensajes de error claros
- Espacio reservado para Google SSO (pendiente)

### `/chat` — Workspace del asistente

- Header con identidad del sistema y menú de usuario
- Panel de conversación con historial de mensajes
- Sidebar de historial de consultas

### Consola administrativa

- `/admin/manuals` — Listado de manuales con estado de ingestión y progreso. Modal
  de carga múltiple con título extraído del nombre del PDF, selector de idioma y
  categorías por archivo. El modal de edición permite cambiar título, notas y
  categorías (el modelo de robot y la versión de controlador solo se muestran).
- `/admin/users` — Alta, edición y borrado de usuarios.
- `/admin/roles` — Permisos por rol.
- `/admin/settings` — Parámetros de Gemini/RAG ajustables en caliente.
- `/admin/audit` — Registro de eventos con filtros.

### `/settings` y `/profile` — Configuración de perfil

- Edición de nombre y preferencias de idioma
- Cambio de contraseña con validación de reglas

### Rutas auxiliares

| Ruta | Comportamiento |
|---|---|
| `/profile` | Redirige a `/settings` |
| `/admin` | Redirige a `/admin/manuals` |

---

## Criterios de diseño

| Criterio | Descripción |
|---|---|
| **Tema oscuro unificado** | Todos los screens usan tokens de diseño centralizados (`bg`, `surface`, `ink`, `accent`) definidos en Tailwind CSS v4 |
| **Consistencia visual** | Mismo lenguaje de diseño entre login, workspace y administración |
| **Navegación por sesión** | Las rutas se protegen según la sesión activa, sin credenciales en el frontend |
| **Layout adaptable** | Estructura responsive que prioriza la legibilidad del código PAC |
| **Barrel exports** | Cada feature module exporta via `index.ts` para imports limpios |
