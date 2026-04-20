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

- Autenticación con correo autorizado y contraseña
- Opción para mostrar/ocultar contraseña
- Validación amigable con mensajes de error claros
- Espacio reservado para Google SSO (pendiente)

### `/app` — Workspace del asistente

- Sidebar izquierdo: configuración del robot
- Panel central: conversación y código PAC
- Sidebar derecho: referencias e historial

### `/admin` — Consola administrativa

- Resumen operativo del sistema
- Usuarios autorizados (visualización)
- Parámetros del modelo Gemini (visualización)
- Base documental (visualización)

---

## Criterios de diseño

| Criterio | Descripción |
|---|---|
| **Consistencia visual** | Mismo lenguaje de diseño entre login, workspace y administración |
| **Navegación por sesión** | Las rutas se protegen según la sesión activa, sin credenciales en el frontend |
| **Layout adaptable** | Estructura responsive que prioriza la legibilidad del código PAC |
| **Contexto técnico explícito** | La configuración del robot siempre es visible junto a la conversación |
