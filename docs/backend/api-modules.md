# Módulos del Backend — Referencia de Endpoints

Todos los endpoints están bajo el prefijo `/api/v1` (montado en
[main.py](../../apps/api/src/main.py) → [router.py](../../apps/api/src/api/v1/router.py)).
La autenticación es por **cookie HttpOnly `rc7_session`** con JWT firmado (HS256).

**Auth requerida:**
- `No` — endpoint público.
- `*` — cualquier sesión válida (`get_current_user`, 401 si no hay cookie válida).
- `admin` — sesión con **rol activo** admin (`get_current_admin_user`, 403 si el rol activo no es admin).

> El frontend nunca llama al API directamente: pega a `/api/v1/*` en su propio origen y el
> proxy de Next.js ([route.ts](../../apps/web/src/app/api/v1/[...path]/route.ts)) reenvía a
> `INTERNAL_API_URL` (`http://api:8000`) propagando la cookie de sesión.

---

## Health — `/api/v1/health` · [health.py](../../apps/api/src/api/v1/routes/health.py)

| Método | Ruta | Auth | Respuesta |
|---|---|---|---|
| `GET` | `/api/v1/health/` | No | `{"status": "ok"}` (sin timestamp ni versión) |

---

## Auth — `/api/v1/auth` · [auth.py](../../apps/api/src/api/v1/routes/auth.py)

| Método | Ruta | Auth | Descripción · errores |
|---|---|---|---|
| `GET` | `/auth/providers` | No | Lista de proveedores: `["google"]` con nota de que el SSO **no está implementado** aún. |
| `POST` | `/auth/login` | No | Login email+password → `SessionResponse` y `Set-Cookie`. **401** si credenciales inválidas o usuario inactivo (audita `AUTH_FAILED`). Audita `AUTH_LOGIN` en éxito. |
| `GET` | `/auth/me` | `*` | `SessionResponse` del usuario y rol activo. |
| `POST` | `/auth/switch-role` | `*` | Cambia el rol activo y renueva la cookie. **403** si el usuario no tiene ese rol. |
| `POST` | `/auth/logout` | `*` (best-effort) | Borra la cookie; siempre `200`. Audita `AUTH_LOGOUT` si había sesión. |

`SessionResponse`: `{ email, display_name, role, available_roles[] }`.

---

## Profile — `/api/v1/profile` · [profile.py](../../apps/api/src/api/v1/routes/profile.py)

| Método | Ruta | Auth | Descripción · errores |
|---|---|---|---|
| `GET` | `/profile` | `*` | `{ email, display_name, settings }`. |
| `PUT` | `/profile` | `*` | Actualiza **`display_name` y `settings`** (el email **no** se cambia). Renueva la cookie. |
| `POST` | `/profile/password` | `*` | Cambia contraseña. **400** si la actual es incorrecta, si la nueva es igual a la actual, o si no cumple las reglas (8-16 chars, mayúscula, minúscula, dígito, símbolo). |

> Nota: el endpoint de contraseña es **`POST`** (no `PUT`).

---

## Chat — `/api/v1/chat` · [chat.py](../../apps/api/src/api/v1/routes/chat.py)

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `POST` | `/chat/generate` | `*` | Ejecuta el pipeline RAG de 4 fases y responde **SSE** (`text/event-stream`). Con `ENABLE_STREAMING=false` corre síncrono y emite un único evento `done` (**503** si el pipeline falla en ese modo). |
| `GET` | `/chat/history?limit=&offset=` | `*` | Historial del usuario, paginado (`limit` default 50). |
| `DELETE` | `/chat/history/{item_id}` | `*` | Borra una entrada propia. **404** si no existe o no es del usuario. `204`. |

**Request `POST /chat/generate`** (`ChatRequest`, [schemas/chat.py](../../apps/api/src/api/v1/schemas/chat.py)):
`prompt` (req), `robot_type`, `controller`, `io_profile`, `payload_kg`, `tool_number`,
`max_speed_pct`, `hand_type`, `install_type`, `has_io_expansion`, `expansion_io_inputs`,
`expansion_io_outputs`, `current_code`.

**Eventos SSE:**
```
data: {"type":"chunk","content":"<texto parcial del JSON>"}
data: {"type":"done","summary":"...","pac_code":"MOVE P,P1  ' fuente: S1","references":[{"source_id":"S1","title":"...","page":"42"}],"advisories":["..."]}
data: {"type":"error","message":"Pipeline fallido"}     ← si falla a mitad del stream
```
Tras `done`, el endpoint persiste la entrada de historial (podando a `history_max_entries`) y
audita `CHAT_QUERY` (best-effort; nunca rompe la respuesta).

---

## Manuals — `/api/v1/manuals` · [manuals.py](../../apps/api/src/api/v1/routes/manuals.py)

> **Todas** las rutas de manuales requieren **`admin`**.

| Método | Ruta | Descripción · errores |
|---|---|---|
| `GET` | `/manuals` | Lista todos los manuales (rellena `sha256` perezosamente desde MinIO si falta). |
| `GET` | `/manuals/review-summaries` | Resúmenes de revisión semántica por manual. |
| `GET` | `/manuals/{manual_id}` | Detalle de un manual. **404** si no existe. |
| `GET` | `/manuals/{manual_id}/file` | Devuelve el PDF original (`inline`). **503** si MinIO falla. |
| `POST` | `/manuals` | **multipart/form-data**: `title` (3-255), `file` (PDF), `robot_model?`, `controller_version?`, `document_language` (`es`/`en`), `category?[]`, `notes?`, `as_new_version?`. `201`. **400** si no es PDF o está vacío; **409** si el SHA-256 ya existe (salvo `as_new_version=true`); **503** si MinIO falla. Audita `MANUAL_UPLOADED`. |
| `PUT` | `/manuals/{manual_id}` | Actualiza `title`, `notes`, `categories`. Audita `MANUAL_UPDATED`. |
| `POST` | `/manuals/{manual_id}/retry` | Reencola un manual. **409** si está `processing` o `indexed`. |
| `POST` | `/manuals/{manual_id}/cancel` | Cancela; borra chunks y marca `failed`. **409** si no está `pending`/`processing`. |
| `POST` | `/manuals/cleanup-stale-processing?older_than_minutes=` | Reencola manuales atascados en `processing` (umbral 1-1440 min, default 10). |
| `DELETE` | `/manuals/{manual_id}` | **Elimina físicamente** el manual + chunks + reviews + PDF en MinIO. `204`. Audita `MANUAL_DELETED`. |

**Estados:** `pending` → `processing` → `indexed` / `failed`.

---

## Admin — `/api/v1/admin` · [admin.py](../../apps/api/src/api/v1/routes/admin.py)

> Todas requieren **`admin`**.

| Método | Ruta | Descripción · errores |
|---|---|---|
| `GET` | `/admin/status` | `{ manuals_indexed, active_users, pending_jobs }`. |
| `GET` | `/admin/roles/permissions` | Lista permisos de rol. |
| `POST` | `/admin/roles/permissions` | Crea permiso. `201`. **409** si la clave existe. |
| `PUT` | `/admin/roles/permissions/{permission_id}` | Actualiza permiso. **404** si no existe. |
| `DELETE` | `/admin/roles/permissions/{permission_id}` | Borra permiso. `204`. **404** si no existe. |
| `GET` | `/admin/users` | Lista usuarios. |
| `GET` | `/admin/users/{user_id}` | Detalle. **404** si no existe. |
| `POST` | `/admin/users` | Crea usuario. `201`. **409** email duplicado; **400** contraseña débil. Audita `ADMIN_USER_CREATED`. |
| `PUT` | `/admin/users/{user_id}` | Actualiza. **400** si te auto-quitas admin / te desactivas, o si demota al último admin activo. Audita `ADMIN_USER_UPDATED`. |
| `DELETE` | `/admin/users/{user_id}` | **Elimina físicamente** el usuario. `204`. **400** si es uno mismo o el último admin. Audita `ADMIN_USER_DELETED`. |

> La ruta de permisos es `/admin/roles/permissions` (no `/admin/role-permissions`).

---

## Settings — `/api/v1/admin/settings` · [settings.py](../../apps/api/src/api/v1/routes/settings.py)

> Todas requieren **`admin`**.

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/admin/settings` | Lista parámetros con valor actual. |
| `GET` | `/admin/settings/{key}` | Valor de un parámetro. **404** si no existe. |
| `PUT` | `/admin/settings/{key}` | Actualiza el valor. **404** si no existe. Audita `SETTING_UPDATED`. |
| `POST` | `/admin/settings/reset` | Restaura defaults. Audita `SETTING_RESET`. |

Ver [settings-module.md](./settings-module.md) para el catálogo completo y cuáles se leen realmente.

---

## Audit — `/api/v1/admin/audit` · [audit.py](../../apps/api/src/api/v1/routes/audit.py)

> Todas requieren **`admin`**.

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/admin/audit` | Lista paginada. Filtros: `event_type`, `actor_id`, `resource_type`, `date_from`, `date_to`, `page` (≥1), `page_size` (1-200, default 50). |
| `GET` | `/admin/audit/{log_id}` | Detalle por UUID. **404** si no existe. |

Ver [audit-module.md](./audit-module.md) para la lista de tipos de evento.
