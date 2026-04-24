# Módulos del Backend

Detalle de los módulos de la API, organizados por estado de implementación.

---

## Módulos implementados

### `auth`

Gestión completa del ciclo de autenticación:

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/auth/login` | `POST` | Inicio de sesión con correo y contraseña |
| `/api/v1/auth/me` | `GET` | Información de la sesión actual |
| `/api/v1/auth/switch-role` | `POST` | Cambio de rol activo (admin ↔ user) |
| `/api/v1/auth/logout` | `POST` | Cierre de sesión |

Implementa firma y lectura de cookies de sesión con JWT (HttpOnly, Secure en producción).

### `profile`

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/profile` | `GET` | Datos del perfil del usuario autenticado |
| `/api/v1/profile` | `PATCH` | Actualización de nombre y preferencias |
| `/api/v1/profile/password` | `PUT` | Cambio de contraseña con verificación de la actual |

### `health`

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/health/` | `GET` | Healthcheck para diagnóstico y orquestación Docker |

### `chat`

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/chat/generate` | `POST` | Generación de respuesta RAG con Gemini |
| `/api/v1/chat/history` | `GET` | Historial de conversaciones del usuario |

Implementa un pipeline RAG en dos fases:
1. **Fase 1 (HyDE):** consulta directa a Gemini con prompt simplificado para generar una respuesta hipotética que sirve como base de recuperación.
2. **Fase 2 (RAG):** embedding de `(consulta + respuesta_fase1)` → recuperación de chunks relevantes → respuesta final con contexto documental.

Comportamiento adicional:
- El historial por usuario se poda automáticamente a las 50 entradas más recientes.
- Timeout configurable vía `GEMINI_TIMEOUT_SECONDS` (default: 300 s).
- Manejo de errores con respuesta HTTP 503 ante fallos del pipeline.

### `admin`

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/admin/status` | `GET` | Estado administrativo del sistema (requiere rol admin) |

Contrato inicial para sostener la consola administrativa del frontend. Protegido con `get_current_admin_user`.

---

## Módulos parciales

### `manuals`

Gestión inicial de la base documental:

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/manuals` | `GET` | Lista los manuales registrados |
| `/api/v1/manuals/{id}` | `GET` | Devuelve el detalle de un manual |
| `/api/v1/manuals` | `POST` | Carga un PDF a MinIO y persiste sus metadatos |

Implementado en una primera fase: registro del manual, almacenamiento en MinIO y estado inicial de ingestión (`pending`). Pendiente: versionado, reprocesamiento, integración automática con el worker y seguimiento detallado del pipeline.

### `users`

El modelo `User` y la persistencia para autenticación están implementados. Pendiente: CRUD administrativo completo (creación, edición, desactivación de usuarios).

---

## Módulos planificados

### `retrieval`

Búsqueda y recuperación de contexto:
- Consulta vectorial en pgvector
- Filtrado por aplicabilidad técnica (tipo de robot, ejes, visión)
- Citación por página y sección del manual original

### `settings`

Configuración administrativa del sistema:
- Parámetros del modelo Gemini (temperatura, tokens, etc.)
- Prompts del sistema
- Políticas de respuesta

### `audit`

Registro de eventos del sistema:
- Acciones administrativas
- Cambios de configuración
- Eventos de ingestión documental
