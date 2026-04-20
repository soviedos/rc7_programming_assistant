# Estado del Proyecto

Resumen del progreso de implementación del RC7 Programming Assistant.

---

## Implementado

| Componente | Detalle |
|---|---|
| **Autenticación** | Login con correo/contraseña, sesión por cookie HttpOnly, JWT firmado |
| **Gestión de roles** | Cambio de rol activo entre `admin` y `user` |
| **Bootstrap admin** | Creación automática del administrador inicial por variables de entorno |
| **Frontend** | Login con validación, workspace del asistente, consola administrativa |
| **Rutas protegidas** | Navegación condicionada por sesión y rol activo |
| **Stack Docker** | 6 servicios orquestados con healthchecks y dependencias declarativas |
| **Testing** | Suites automatizadas en backend (pytest), frontend (vitest) y worker (pytest) |

## En desarrollo

| Componente | Detalle |
|---|---|
| **Google SSO** | Autenticación con cuentas de Google |
| **CRUD administrativo** | Creación, edición y desactivación de usuarios desde la consola |
| **Ingestión documental** | Pipeline de parsing, chunking y embeddings sobre manuales PDF |
| **Retrieval** | Búsqueda vectorial con pgvector y filtrado por aplicabilidad técnica |
| **Integración Gemini** | Generación de respuestas con contexto RAG |
| **Auditoría** | Registro de acciones administrativas y eventos del sistema |

---

## Nota sobre el estado actual

El proyecto cuenta con una base ejecutable completa: la autenticación, la navegación por perfil y el stack contenedorizado están implementados y probados. Los paneles de administración y el workspace del asistente utilizan datos de ejemplo en las secciones que dependen de las capas pendientes (chat con Gemini, retrieval, gestión de manuales).
