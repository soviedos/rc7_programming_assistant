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
| **Ingestión documental** | El worker procesa manuales pendientes: extrae texto con pypdf, genera chunks estructurales (párrafos por página, máx. 1200 chars), revisión semántica y autocorrección con Gemini de **todos los chunks** (sin muestreo por defecto), genera embeddings con `gemini-embedding-2` (3072-dim) e indexa en pgvector (`vector(3072)` + HNSW). Límite de 3 reinicios automáticos tras crash del worker (`_MAX_CRASH_RETRIES = 3`). |
| **Cancelación de manuales** | `POST /api/v1/manuals/{id}/cancel` permite al administrador detener un manual en estado `pending` o `processing`. Elimina los chunks parciales y marca el manual como `failed`. Disponible desde el panel de administración con el botón "Detener". |
| **CRUD administrativo** | Creación, edición y desactivación de usuarios y gestión de permisos por rol desde la consola |
| **Retrieval RAG** | Búsqueda vectorial con pgvector (distancia coseno `<=>` + índice HNSW sobre cast `halfvec`); pool top-50 re-rankeado por `similitud · compatibilidad de hardware · categoría`; top-24 chunks con presupuesto de 32 000 caracteres. Trazabilidad de fuentes con IDs `S1…Sn` y comentarios `' fuente: SX` en el código PAC. |
| **Integración Gemini** | Pipeline RAG de 4 fases con HyDE: respuesta hipotética → embedding + retrieval → contexto → respuesta final con JSON estructurado |
| **Generación de código PAC** | Genera programa principal + archivos `dio_tab.h` y `var_tab.h` como un bloque único; las macros reflejan el perfil I/O del robot configurado |
| **Frontend** | Login profesional con identidad RobLab/CENFOTEC, tema oscuro unificado, workspace del asistente, consola de manuales con extracción automática de metadatos, panel de configuración de perfil |
| **Rutas protegidas** | Navegación condicionada por sesión y rol activo |
| **Stack Docker** | 5 servicios orquestados con healthchecks y dependencias declarativas: `web`, `api`, `worker`, `postgres`, `minio`. Uvicorn con `--timeout-keep-alive 120` para soportar peticiones largas de Gemini. |
| **Testing** | Suites automatizadas en backend (pytest), frontend (vitest) y worker (pytest) |
| **Módulo settings** | Las 9 claves de `DEFAULT_SETTINGS`, configurables desde la consola admin: Gemini (`gemini_temperature`, `hyde_temperature`, `gemini_max_tokens`, `gemini_timeout_seconds`), RAG (`rag_top_k_chunks`, `rag_context_budget_chars`, `rag_candidate_pool`), el prompt del sistema (`system_prompt_pac`) y `history_max_entries`. Persistidos en `system_settings`. Cambios efectivos en tiempo de ejecución sin reinicio del stack. |
| **Módulo audit** | Registro de eventos del sistema: autenticación, acciones administrativas, cambios de configuración, eventos del pipeline de ingestión y consultas del asistente. Almacenado en `audit_log`. Log paginado con filtros por tipo de evento, actor, tipo de recurso y rango de fecha. El servicio `log_event()` nunca lanza excepción. |
| **Streaming SSE** | `POST /api/v1/chat/generate` transmite tokens en tiempo real vía `StreamingResponse` con `media_type="text/event-stream"`. Emite eventos `chunk`, `done` y `error`. Incluye comentarios keepalive cada 15 segundos para soportar respuestas largas de Gemini. Fallback síncrono disponible con `ENABLE_STREAMING=false`. |

## Pendiente

| Componente | Detalle |
|---|---|
| **Google SSO** | Autenticación con cuentas de Google |

---

## Nota sobre el estado actual

El proyecto cuenta con una implementación completa de todas las funcionalidades principales: autenticación JWT, rutas protegidas por rol, pipeline RAG de 4 fases con HyDE y streaming SSE, CRUD administrativo de usuarios, ingestión documental completa (parsing → chunking → revisión semántica → embeddings → indexación pgvector), módulo de settings con parámetros configurables en caliente, módulo de auditoría con registro inmutable de eventos, y el stack completamente contenedorizado. Queda pendiente la integración con Google SSO.
