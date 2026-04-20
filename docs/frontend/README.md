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

### `/admin/manuals` — Consola administrativa

- Listado de manuales registrados con estado de ingestión
- Modal de carga con extracción automática de metadatos desde nombre del PDF
- Formulario editable para título, modelo de robot, versión de controlador e idioma

### `/settings` — Configuración de perfil

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
