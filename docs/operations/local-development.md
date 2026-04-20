# Desarrollo Local

Guía para levantar y operar el sistema completo en un entorno de desarrollo local.

---

## Requisitos previos

- Docker >= 24.0
- Docker Compose >= 2.20
- Archivo `.env` configurado en la raíz del proyecto

---

## Servicios del stack

| Servicio | Imagen | Puerto | Descripción |
|---|---|---|---|
| `web` | Next.js (custom) | 3000 | Frontend |
| `api` | FastAPI (custom) | 8000 | Backend |
| `worker` | Python (custom) | — | Pipeline documental |
| `postgres` | PostgreSQL | 5432 | Base de datos |
| `redis` | Redis | 6379 | Cache y colas |
| `minio` | MinIO | 9000 / 9001 | Object storage |

---

## Arranque

```bash
# Construir y levantar todos los servicios
docker compose up --build -d
```

## Verificación

```bash
# Estado de los contenedores
docker compose ps

# Healthcheck de la API
curl -s http://localhost:8000/api/v1/health/ | python3 -m json.tool

# Frontend accesible
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

---

## URLs locales

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API REST | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| MinIO API | http://localhost:9000 |
| MinIO Console | http://localhost:9001 |

---

## Comandos útiles

### Logs

```bash
docker compose logs --tail=100 web
docker compose logs --tail=100 api
docker compose logs --tail=100 worker
```

### Shell interactivo

```bash
docker compose exec web sh
docker compose exec api sh
docker compose exec worker sh
```

### Reiniciar un servicio

```bash
docker compose restart api
```

### Reconstruir un servicio específico

```bash
docker compose up --build -d api
```

---

## Variables de entorno

| Variable | Descripción | Requerida |
|---|---|---|
| `BOOTSTRAP_ADMIN_EMAIL` | Correo del administrador inicial | Sí |
| `BOOTSTRAP_ADMIN_PASSWORD` | Contraseña del administrador inicial | Sí |
| `BOOTSTRAP_ADMIN_NAME` | Nombre del administrador inicial | No |
| `JWT_SECRET` | Secreto para firmar tokens JWT | Sí |
| `SESSION_COOKIE_NAME` | Nombre de la cookie de sesión | No |
| `SESSION_TTL_MINUTES` | Duración de la sesión en minutos | No |
| `POSTGRES_*` | Configuración de conexión a PostgreSQL | No (valores por defecto) |
| `REDIS_*` | Configuración de conexión a Redis | No (valores por defecto) |

> Copie `.env.example` como `.env` y ajuste los valores antes de levantar el stack.

---

## Reglas operativas

- El frontend **no debe contener** credenciales ni secretos hardcodeados
- La autenticación se resuelve **exclusivamente** desde el backend
- Cualquier cambio funcional debe actualizar documentación y pruebas en la misma iteración
- La ejecución de servicios, shells y pruebas se realiza **dentro de Docker**
