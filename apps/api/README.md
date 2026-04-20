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
| Redis | Conexión con cache y colas |

---

## Responsabilidades implementadas

- Autenticación con correo y contraseña
- Sesión por cookie HttpOnly con JWT firmado
- Cambio de rol activo (admin ↔ user)
- Bootstrap del administrador por variables de entorno
- Contratos base para chat y administración
- Healthcheck para orquestación Docker

## Responsabilidades planificadas

- CRUD administrativo de usuarios
- Integración con Google Gemini
- Retrieval sobre manuales indexados con pgvector
- Configuración administrativa persistente
- Auditoría de acciones operativas

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
| `POST` | `/api/v1/chat/generate` | Generación de respuesta |

> Documentación interactiva completa en http://localhost:8000/docs

---

## Pruebas

```bash
docker compose exec api python -m pytest
```

Las pruebas utilizan SQLite en memoria con overrides de dependencias de FastAPI.
