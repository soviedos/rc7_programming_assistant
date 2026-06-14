# API — Backend FastAPI

Backend principal del RC7 Programming Assistant, responsable de la autenticación, orquestación de servicios y contratos HTTP.

---

## Stack técnico

| Tecnología | Uso |
|---|---|
| FastAPI | Framework web |
| SQLAlchemy | ORM y acceso a datos |
| Pydantic | Validación y configuración |
| PyJWT | Firma y verificación de tokens |
| pwdlib (Argon2) | Hashing de contraseñas |
| psycopg | Driver PostgreSQL |
| pgvector | Tipo de columna `Vector(3072)` + distancia coseno (`<=>` / `halfvec`) |
| google-genai SDK | Pipeline RAG con Gemini (`gemini-3.5-flash`, `gemini-embedding-2`) |
| MinIO | Almacenamiento de manuales PDF |

---

## Responsabilidades implementadas

- Autenticación con correo y contraseña, sesión por cookie HttpOnly con JWT firmado
- Cambio de rol activo (admin ↔ user) y bootstrap del administrador
- Pipeline RAG de 4 fases con HyDE y streaming SSE
- Retrieval con pgvector: distancia coseno `<=>` (HNSW) + re-rank por compatibilidad de
  hardware del robot y categoría; trazabilidad de fuentes con IDs `S1…Sn`
- CRUD administrativo de usuarios y permisos por rol
- Configuración administrativa persistente (`system_settings`, en caliente)
- Auditoría de acciones operativas (`audit_log`)
- Registro y carga de manuales PDF a MinIO + trigger de ingestión
- Healthcheck para orquestación Docker

---

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Root con información del servicio |
| `GET` | `/api/v1/health/` | Healthcheck |
| `POST` | `/api/v1/auth/login` | Inicio de sesión |
| `GET` | `/api/v1/auth/me` | Sesión actual |
| `POST` | `/api/v1/auth/switch-role` | Cambio de rol |
| `POST` | `/api/v1/auth/logout` | Cierre de sesión |
| `GET` | `/api/v1/admin/status` | Estado administrativo |
| `GET` | `/api/v1/manuals` | Listado administrativo de manuales |
| `GET` | `/api/v1/manuals/{id}` | Detalle de un manual registrado |
| `POST` | `/api/v1/manuals` | Carga de manual PDF y registro de metadatos |
| `POST` | `/api/v1/chat/generate` | Generación de respuesta |

> Documentación interactiva completa en http://localhost:8000/docs

---

## Pruebas

```bash
docker compose exec api python -m pytest
```

Las pruebas corren contra una base PostgreSQL dedicada `rc7_test` (auto-creada por el
fixture de conftest, con la extensión `vector` habilitada) y overrides de dependencias de FastAPI.
