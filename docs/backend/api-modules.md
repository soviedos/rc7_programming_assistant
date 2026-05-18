# Módulos del Backend — Referencia de Endpoints

Todos los endpoints están bajo el prefijo `/api/v1`.
La autenticación se realiza mediante cookie HttpOnly (`rc7_session`) con JWT firmado.

**Roles:**
- `user` — usuario estándar
- `admin` — acceso completo a las rutas de administración
- `*` — cualquier usuario autenticado

---

## Health — `/api/v1/health`

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/health/` | No | Estado del servicio + timestamp + versión |

---

## Auth — `/api/v1/auth`

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | No | Login con email y contraseña; emite cookie HttpOnly JWT |
| `POST` | `/api/v1/auth/logout` | `*` | Cierra sesión; elimina la cookie |
| `GET` | `/api/v1/auth/me` | `*` | Devuelve el perfil del usuario autenticado |
| `POST` | `/api/v1/auth/switch-role` | `*` | Cambia el rol activo; renueva la cookie JWT |

---

## Profile — `/api/v1/profile`

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/profile/` | `*` | Perfil del usuario autenticado |
| `PUT` | `/api/v1/profile/` | `*` | Actualiza nombre y/o email |
| `PUT` | `/api/v1/profile/password` | `*` | Cambia la contraseña (requiere contraseña actual) |

---

## Chat — `/api/v1/chat`

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `POST` | `/api/v1/chat/generate` | `*` | **[SSE]** Ejecuta el pipeline RAG de 4 fases y transmite la respuesta como Server-Sent Events |
| `GET` | `/api/v1/chat/history` | `*` | Lista el historial de chat del usuario (paginado) |
| `DELETE` | `/api/v1/chat/history/{id}` | `*` | Elimina una entrada específica del historial |

### Protocolo SSE — `POST /api/v1/chat/generate`

**Request body:**
```json
{
  "prompt": "¿Cómo muevo el brazo a una posición absoluta?",
  "robot_type": "VP-6242G",
  "controller": "RC7",
  "io_profile": "default",
  "payload_kg": 2.0,
  "tool_number": 1
}
```

**Eventos SSE emitidos:**
```
data: {"type": "chunk", "content": "Puedes usar..."}
data: {"type": "chunk", "content": " la instrucción MOVE..."}
...
data: {"type": "done", "summary": "...", "pac_code": "MOVE P1,S=50", "references": [{"title": "...", "page": 42}]}
```

**Evento de error:**
```
data: {"type": "error", "message": "Pipeline fallido"}
```

---

## Manuals — `/api/v1/manuals`

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/manuals/` | `*` | Lista todos los manuales con estado de ingestión |
| `GET` | `/api/v1/manuals/review-summaries` | `admin` | Lista resúmenes de revisión semántica de chunks |
| `GET` | `/api/v1/manuals/{manual_id}` | `*` | Detalle de un manual específico |
| `GET` | `/api/v1/manuals/{manual_id}/file` | `admin` | Descarga el PDF original desde MinIO |
| `POST` | `/api/v1/manuals/` | `admin` | Sube un PDF; crea registro y dispara ingestión en el worker |
| `PUT` | `/api/v1/manuals/{manual_id}` | `admin` | Actualiza metadatos (título, categoría, descripción) |
| `POST` | `/api/v1/manuals/{manual_id}/retry` | `admin` | Reintenta la ingestión de un manual fallido |
| `POST` | `/api/v1/manuals/cleanup-stale-processing` | `admin` | Libera manuales atascados en estado `processing` |
| `DELETE` | `/api/v1/manuals/{manual_id}` | `admin` | Elimina manual, chunks, embeddings y archivo en MinIO |

**Estados de ingestión:** `pending` → `processing` → `indexed` / `failed`

---

## Admin — `/api/v1/admin`

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/admin/status` | `admin` | Estado del sistema: conteos de manuales, usuarios y jobs pendientes |
| `GET` | `/api/v1/admin/role-permissions` | `admin` | Lista los permisos de rol configurados |
| `POST` | `/api/v1/admin/role-permissions` | `admin` | Crea un permiso de rol |
| `PUT` | `/api/v1/admin/role-permissions/{id}` | `admin` | Actualiza un permiso de rol |
| `DELETE` | `/api/v1/admin/role-permissions/{id}` | `admin` | Elimina un permiso de rol |
| `GET` | `/api/v1/admin/users` | `admin` | Lista todos los usuarios |
| `GET` | `/api/v1/admin/users/{user_id}` | `admin` | Detalle de un usuario |
| `POST` | `/api/v1/admin/users` | `admin` | Crea un nuevo usuario |
| `PUT` | `/api/v1/admin/users/{user_id}` | `admin` | Actualiza datos y roles de un usuario |
| `DELETE` | `/api/v1/admin/users/{user_id}` | `admin` | Deshabilita un usuario (no lo elimina físicamente) |

---

## Settings — `/api/v1/admin/settings`

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/admin/settings/` | `admin` | Lista todos los parámetros configurables con sus valores actuales |
| `GET` | `/api/v1/admin/settings/{key}` | `admin` | Obtiene el valor de un parámetro específico |
| `PUT` | `/api/v1/admin/settings/{key}` | `admin` | Actualiza el valor de un parámetro; genera evento `SETTING_UPDATED` en audit |
| `POST` | `/api/v1/admin/settings/reset` | `admin` | Restaura todos los parámetros a sus valores por defecto; genera evento `SETTING_RESET` |

Ver [docs/backend/settings-module.md](./settings-module.md) para la tabla completa de parámetros.

---

## Audit — `/api/v1/admin/audit`

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/admin/audit/` | `admin` | Lista eventos del audit log (paginado, filtros opcionales) |
| `GET` | `/api/v1/admin/audit/{log_id}` | `admin` | Detalle de un evento de auditoría |

**Query params para listado:**
`event_type`, `actor_id`, `resource_type`, `date_from`, `date_to`, `page` (default 1), `page_size` (default 50, máx 200)

Ver [docs/backend/audit-module.md](./audit-module.md) para la lista completa de eventos.
