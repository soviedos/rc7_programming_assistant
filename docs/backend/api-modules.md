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

### `health`

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/health/` | `GET` | Healthcheck para diagnóstico y orquestación Docker |

### `chat`

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/chat/generate` | `POST` | Generación de respuesta del asistente |

Actualmente expone un contrato placeholder que devuelve resumen, código PAC y referencias. Pendiente de integración con Gemini y retrieval.

### `admin`

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/admin/status` | `GET` | Estado administrativo del sistema |

Contrato inicial para sostener la consola administrativa del frontend.

---

## Módulos parciales

### `users`

El modelo `User` y la persistencia para autenticación están implementados. Pendiente: CRUD administrativo completo (creación, edición, desactivación de usuarios).

---

## Módulos planificados

### `manuals`

Gestión de la base documental:
- Carga de PDFs a MinIO
- Versionado de documentos
- Metadatos por robot y versión del controlador

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
