# Estado del Proyecto

Resumen del progreso de implementación del RC7 Programming Assistant.

---

## Implementado

| Componente | Detalle |
|---|---|
| **Autenticación** | Login con correo/contraseña, sesión por cookie HttpOnly, JWT firmado |
| **Gestión de roles** | Cambio de rol activo entre `admin` y `user` |
| **Bootstrap admin** | Creación automática del administrador inicial por variables de entorno |
| **Manuales** | Registro administrativo de PDFs, carga a MinIO y metadatos persistidos |
| **Ingestión documental base** | El worker procesa manuales pendientes, extrae texto, genera chunks y actualiza estado |
| **Frontend** | Login profesional con identidad RobLab/CENFOTEC, tema oscuro unificado, workspace del asistente, consola de manuales con extracción automática de metadatos, panel de configuración de perfil |
| **Rutas protegidas** | Navegación condicionada por sesión y rol activo |
| **Stack Docker** | 6 servicios orquestados con healthchecks y dependencias declarativas; uvicorn con `--timeout-keep-alive 120` para soportar peticiones largas de Gemini |
| **Testing** | Suites automatizadas en backend (pytest), frontend (vitest) y worker (pytest) |

## En desarrollo

| Componente | Detalle |
|---|---|
| **Google SSO** | Autenticación con cuentas de Google |
| **CRUD administrativo** | Creación, edición y desactivación de usuarios desde la consola |
| **Ingestión documental avanzada** | Clasificación técnica, embeddings y enriquecimiento sobre manuales ya procesados |
| **Retrieval** | Búsqueda vectorial con pgvector integrada en el pipeline RAG; pendiente filtrado por aplicabilidad técnica |
| **Integración Gemini** | Pipeline RAG con HyDE (dos fases): respuesta hipotética → retrieval → respuesta final con contexto documental |
| **Auditoría** | Registro de acciones administrativas y eventos del sistema |

---

## Nota sobre el estado actual

El proyecto cuenta con una base ejecutable completa: la autenticación, la navegación por perfil, el registro inicial de manuales, la ingesta documental base y el stack contenedorizado están implementados y probados. El workspace del asistente ya genera respuestas reales mediante el pipeline RAG con Gemini. Los paneles de administración y algunas secciones del workspace aún utilizan datos de ejemplo en las partes que dependen de funcionalidades pendientes (SSO, retrieval con filtrado por aplicabilidad, auditoría).
