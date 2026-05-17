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
| **Ingestión documental** | El worker procesa manuales pendientes: extrae texto con pypdf, genera chunks semánticos, revisión y autocorrección con Gemini, genera embeddings con `gemini-embedding-001` e indexa en pgvector |
| **CRUD administrativo** | Creación, edición y desactivación de usuarios y gestión de permisos por rol desde la consola |
| **Retrieval RAG** | Búsqueda vectorial con pgvector integrada en el pipeline de chat |
| **Integración Gemini** | Pipeline RAG con HyDE (dos fases): respuesta hipotética → embedding + retrieval → respuesta final con contexto documental |
| **Frontend** | Login profesional con identidad RobLab/CENFOTEC, tema oscuro unificado, workspace del asistente, consola de manuales con extracción automática de metadatos, panel de configuración de perfil |
| **Rutas protegidas** | Navegación condicionada por sesión y rol activo |
| **Stack Docker** | 6 servicios orquestados con healthchecks y dependencias declarativas; uvicorn con `--timeout-keep-alive 120` para soportar peticiones largas de Gemini |
| **Testing** | Suites automatizadas en backend (pytest), frontend (vitest) y worker (pytest) |

## Pendiente

| Componente | Detalle |
|---|---|
| **Google SSO** | Autenticación con cuentas de Google |
| **Auditoría** | Registro de acciones administrativas y eventos del sistema |

---

## Nota sobre el estado actual

El proyecto cuenta con una base ejecutable completa: autenticación, navegación por perfil, registro y procesamiento completo de manuales (parsing → chunking → revisión semántica → embeddings → indexación pgvector), pipeline RAG con Gemini operativo, CRUD administrativo de usuarios y el stack contenedorizado están implementados y probados. Quedan pendientes Google SSO y el módulo de auditoría.
