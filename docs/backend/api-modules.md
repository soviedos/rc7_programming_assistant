# Módulos del Backend

Detalle de los módulos de la API.

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
| `/api/v1/profile` | `PUT` | Actualización de nombre y preferencias |
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
| `/api/v1/chat/history/{id}` | `DELETE` | Eliminación de una entrada del historial |

Implementa un pipeline RAG en cuatro fases:
1. **Fase 1 (HyDE):** consulta directa a Gemini con prompt simplificado para generar una respuesta hipotética que sirve como base de recuperación.
2. **Fase 2 (retrieval):** embedding de `(consulta + respuesta_fase1)` → recuperación de los top-6 chunks más relevantes por similitud coseno con boost por categoría.
3. **Fase 3 (contexto):** construcción del contexto documental a partir de los chunks recuperados (presupuesto de 12 000 caracteres).
4. **Fase 4 (respuesta final):** llamada a Gemini con el contexto RAG y el prompt de sistema estructurado; genera JSON con `summary`, `pac_code` y `references`. Si no hay chunks disponibles, genera la respuesta usando solo las reglas de sintaxis PAC del prompt.

Comportamiento adicional:
- El historial por usuario se poda automáticamente a las 50 entradas más recientes.
- Timeout configurable vía `GEMINI_TIMEOUT_SECONDS` (default: 300 s).
- Manejo de errores con respuesta HTTP 503 ante fallos del pipeline.

### `admin`

Consola administrativa protegida con `get_current_admin_user`.

**Estado del sistema:**

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/admin/status` | `GET` | Estado global del sistema (conteo de usuarios, manuales, chunks) |

**Gestión de usuarios:**

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/admin/users` | `GET` | Lista paginada de usuarios |
| `/api/v1/admin/users` | `POST` | Creación de nuevo usuario |
| `/api/v1/admin/users/{id}` | `GET` | Detalle de un usuario |
| `/api/v1/admin/users/{id}` | `PUT` | Actualización de datos del usuario |
| `/api/v1/admin/users/{id}/toggle-active` | `PATCH` | Activación / desactivación del usuario |

**Permisos de rol:**

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/admin/users/{id}/roles` | `GET` | Lista los roles asignados al usuario |
| `/api/v1/admin/users/{id}/roles` | `PUT` | Reemplaza los roles del usuario |

### `manuals`

Gestión de la base documental:

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/manuals` | `GET` | Lista los manuales registrados |
| `/api/v1/manuals/{id}` | `GET` | Devuelve el detalle de un manual |
| `/api/v1/manuals` | `POST` | Carga un PDF a MinIO y persiste sus metadatos |
| `/api/v1/manuals/{id}` | `PUT` | Actualiza los metadatos de un manual |
| `/api/v1/manuals/{id}` | `DELETE` | Elimina el manual y su archivo en MinIO |

Registro del manual, almacenamiento en MinIO y seguimiento del estado de ingestión (`pending` → `processing` → `ready` / `failed`).

---

## Módulos planificados

### `settings`

Configuración administrativa del sistema:
- Parámetros del modelo Gemini (temperatura, tokens, etc.)
- Prompts del sistema
- Políticas de respuesta

### `audit`

Registro de eventos del sistema:
- Acciones administrativas
- Cambios de configuración
- Errores del pipeline de ingestión
- Consultas del asistente
