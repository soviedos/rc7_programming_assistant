# Módulo Audit — Registro de Eventos

El módulo `audit` registra de forma inmutable todos los eventos relevantes del sistema:
autenticación, administración, chat y configuración. Los registros son de solo lectura desde la API.

---

## API

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/admin/audit` | `admin` | Lista eventos con filtros opcionales (paginado) |
| `GET` | `/api/v1/admin/audit/{log_id}` | `admin` | Detalle de un evento específico |

### Parámetros de filtrado (GET /)

| Parámetro | Tipo | Descripción |
|---|---|---|
| `event_type` | `string` | Filtrar por tipo de evento (ej. `AUTH_LOGIN`) |
| `actor_id` | `int` | Filtrar por ID del usuario que realizó la acción |
| `resource_type` | `string` | Filtrar por tipo de recurso afectado (ej. `manual`, `user`) |
| `date_from` | `string` | Eventos desde esta fecha (se espera ISO 8601) |
| `date_to` | `string` | Eventos hasta esta fecha (se espera ISO 8601) |
| `page` | `int` | Número de página (default: 1) |
| `page_size` | `int` | Resultados por página (default: 50, máx: 200) |

> `date_from` / `date_to` se declaran como `str` y se pasan tal cual al `WHERE`: **no hay
> validación de formato**. Un valor inválido no lo rechaza Pydantic con un 422, sino que falla
> en la base de datos.

---

## Campos del registro

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | string | Identificador único del evento (UUID v4 en `VARCHAR(36)`) |
| `event_type` | string | Tipo de evento (ver tabla a continuación) |
| `actor_id` | int | ID del usuario que realizó la acción (nullable) |
| `actor_email` | string | Email del actor en el momento del evento |
| `resource_type` | string | Categoría del recurso afectado (ej. `"user"`, `"manual"`, `"setting"`) |
| `resource_id` | string | ID del recurso específico (nullable) |
| `description` | string | Descripción breve del evento en texto natural |
| `event_metadata` | JSON | Datos adicionales del contexto (ver columna "Metadata" en la tabla de eventos) |
| `ip_address` | string | IP del cliente (nullable: solo lo registran auth y chat) |
| `created_at` | datetime | Timestamp del evento (UTC) |

**Privacidad:** No se almacenan el contenido del prompt del usuario, el texto de la respuesta
del asistente ni el código PAC generado. Solo se registran metadatos del evento.

---

## Tipos de eventos

Solo el módulo de chat pasa `metadata` a `log_event`; en el resto de eventos
`event_metadata` queda en `NULL`. El actor, el recurso afectado y la descripción sí
se registran siempre (columnas `actor_id`, `actor_email`, `resource_type`,
`resource_id`, `description`).

| Tipo de evento | Módulo | Trigger | `event_metadata` |
|---|---|---|---|
| `AUTH_FAILED` | `auth.py` | Intento de login fallido (credenciales incorrectas) | — |
| `AUTH_LOGIN` | `auth.py` | Login exitoso | — |
| `AUTH_LOGOUT` | `auth.py` | Logout del usuario (best-effort, puede no registrarse si la sesión ya expiró) | — |
| `CHAT_QUERY` | `chat.py` | Consulta procesada por el pipeline RAG (streaming o no) | `{"robot_type": "...", "entry_type": "...", "references_count": 6}` |
| `CHAT_QUERY_FAILED` | `chat.py` | La consulta RAG falló | `{"robot_type": "...", "error": "..."}` (error truncado a 300 chars) |
| `ADMIN_USER_CREATED` | `admin.py` | Admin crea un nuevo usuario | — |
| `ADMIN_USER_UPDATED` | `admin.py` | Admin actualiza datos de un usuario | — |
| `ADMIN_USER_DELETED` | `admin.py` | Admin elimina un usuario | — |
| `ADMIN_PERMISSION_CREATED` | `admin.py` | Admin crea un permiso de rol | — |
| `ADMIN_PERMISSION_UPDATED` | `admin.py` | Admin actualiza un permiso de rol | — |
| `ADMIN_PERMISSION_DELETED` | `admin.py` | Admin elimina un permiso de rol | — |
| `SETTING_UPDATED` | `settings.py` | Admin actualiza el valor de un parámetro | — |
| `SETTING_RESET` | `settings.py` | Admin restaura todos los parámetros a sus defaults | — |
| `MANUAL_UPLOADED` | `manuals.py` | Admin sube un manual PDF | — |
| `MANUAL_UPDATED` | `manuals.py` | Admin actualiza metadatos de un manual | — |
| `MANUAL_DELETED` | `manuals.py` | Admin elimina un manual (incluye chunks y archivo MinIO) | — |

---

## Garantías y limitaciones

### ✅ Garantías
- El registro es **append-only** desde la API; no existe endpoint de modificación o borrado.
- El servicio `log_event()` **nunca lanza excepción**; fallos de persistencia se registran
  en el log del proceso Python sin propagarse al caller.
- Solo los eventos de `auth.py` y `chat.py` registran `ip_address`; en el resto queda `NULL`.

### ⚠️ Limitaciones
- **Best-effort:** Si la base de datos no está disponible en el momento del evento, el
  registro se pierde silenciosamente (solo queda en los logs del proceso).
- **Sin reintentos:** No hay cola de eventos ni reintento automático en caso de fallo.
- **AUTH_LOGOUT:** Se registra dentro de un `try/except`; puede no quedar constancia si
  la sesión ya expiró al llamar al endpoint.
- **Sin retención automática:** Los registros no se eliminan automáticamente. Se recomienda
  implementar un job de archivado periódico si el volumen crece.

---

## Ejemplo de respuesta

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "event_type": "CHAT_QUERY",
  "actor_id": 1,
  "actor_email": "user@example.com",
  "resource_type": "chat",
  "resource_id": null,
  "description": "Usuario realizó una consulta al asistente PAC",
  "event_metadata": {
    "robot_type": "VP-6242",
    "entry_type": "code",
    "references_count": 6
  },
  "ip_address": "192.168.1.100",
  "created_at": "2025-05-17T14:32:10.123456Z"
}
```
