# Módulo Audit — Registro de Eventos

El módulo `audit` registra de forma inmutable todos los eventos relevantes del sistema:
autenticación, administración, chat y configuración. Los registros son de solo lectura desde la API.

---

## API

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/admin/audit/` | `admin` | Lista eventos con filtros opcionales (paginado) |
| `GET` | `/api/v1/admin/audit/{log_id}` | `admin` | Detalle de un evento específico |

### Parámetros de filtrado (GET /)

| Parámetro | Tipo | Descripción |
|---|---|---|
| `event_type` | `string` | Filtrar por tipo de evento (ej. `AUTH_LOGIN`) |
| `actor_id` | `UUID` | Filtrar por ID del usuario que realizó la acción |
| `resource_type` | `string` | Filtrar por tipo de recurso afectado (ej. `manual`, `user`) |
| `date_from` | `datetime` | Eventos desde esta fecha (ISO 8601) |
| `date_to` | `datetime` | Eventos hasta esta fecha (ISO 8601) |
| `page` | `int` | Número de página (default: 1) |
| `page_size` | `int` | Resultados por página (default: 50, máx: 200) |

---

## Campos del registro

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | Identificador único del evento |
| `event_type` | string | Tipo de evento (ver tabla a continuación) |
| `actor_id` | UUID | ID del usuario que realizó la acción (nullable) |
| `actor_email` | string | Email del actor en el momento del evento |
| `resource_type` | string | Categoría del recurso afectado (ej. `"user"`, `"manual"`, `"setting"`) |
| `resource_id` | string | ID del recurso específico (nullable) |
| `description` | string | Descripción breve del evento en texto natural |
| `event_metadata` | JSON | Datos adicionales del contexto (ver columna "Metadata" en la tabla de eventos) |
| `ip_address` | string | IP del cliente que originó la acción |
| `created_at` | datetime | Timestamp del evento (UTC) |

**Privacidad:** No se almacenan el contenido del prompt del usuario, el texto de la respuesta
del asistente ni el código PAC generado. Solo se registran metadatos del evento.

---

## Tipos de eventos

| Tipo de evento | Módulo | Trigger | Metadata relevante |
|---|---|---|---|
| `AUTH_FAILED` | `auth.py` | Intento de login fallido (credenciales incorrectas) | `{"email": "..."}` |
| `AUTH_LOGIN` | `auth.py` | Login exitoso | `{"role": "admin"}` |
| `AUTH_LOGOUT` | `auth.py` | Logout del usuario (best-effort, puede no registrarse si la sesión ya expiró) | `{}` |
| `CHAT_QUERY` | `chat.py` | Consulta procesada por el pipeline RAG (streaming o no) | `{"robot_type": "VP-6242G", "entry_type": "program", "chunks_retrieved": 6}` |
| `ADMIN_USER_CREATED` | `admin.py` | Admin crea un nuevo usuario | `{"email": "...", "roles": [...]}` |
| `ADMIN_USER_UPDATED` | `admin.py` | Admin actualiza datos de un usuario | `{"user_id": "...", "fields_changed": [...]}` |
| `ADMIN_USER_TOGGLED` | `admin.py` | Admin desactiva un usuario (soft delete) | `{"user_id": "...", "action": "disable"}` |
| `SETTING_UPDATED` | `settings.py` | Admin actualiza el valor de un parámetro | `{"key": "rag_top_k_chunks", "old_value": "6", "new_value": "8"}` |
| `SETTING_RESET` | `settings.py` | Admin restaura todos los parámetros a sus defaults | `{"keys_reset": [...]}` |
| `MANUAL_UPLOADED` | `manuals.py` | Admin sube un manual PDF | `{"filename": "...", "size_bytes": 1234567}` |
| `MANUAL_UPDATED` | `manuals.py` | Admin actualiza metadatos de un manual | `{"manual_id": "...", "fields_changed": [...]}` |
| `MANUAL_DELETED` | `manuals.py` | Admin elimina un manual (incluye chunks y archivo MinIO) | `{"manual_id": "...", "title": "..."}` |

---

## Garantías y limitaciones

### ✅ Garantías
- El registro es **append-only** desde la API; no existe endpoint de modificación o borrado.
- El servicio `log_event()` **nunca lanza excepción**; fallos de persistencia se registran
  en el log del proceso Python sin propagarse al caller.
- Todos los eventos incluyen `ip_address` del cliente original.

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
  "actor_id": "1c2d3e4f-5a6b-7c8d-9e0f-1a2b3c4d5e6f",
  "actor_email": "user@example.com",
  "resource_type": "chat",
  "resource_id": null,
  "description": "Usuario realizó una consulta al asistente PAC",
  "event_metadata": {
    "robot_type": "VP-6242G",
    "entry_type": "program",
    "chunks_retrieved": 6
  },
  "ip_address": "192.168.1.100",
  "created_at": "2025-05-17T14:32:10.123456Z"
}
```
