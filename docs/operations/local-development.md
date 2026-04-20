# Desarrollo Local

## Objetivo

Levantar el sistema completo de forma reproducible dentro de contenedores.

## Servicios incluidos

- `web`
- `api`
- `worker`
- `postgres`
- `redis`
- `minio`

## Arranque

```bash
docker compose up --build -d
```

## Verificación rápida

```bash
docker compose ps
curl http://localhost:3000
curl http://localhost:8000/api/v1/health/
```

## URLs locales

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

## Comandos útiles

### Logs

```bash
docker compose logs --tail=100 web
docker compose logs --tail=100 api
docker compose logs --tail=100 worker
```

### Shell

```bash
docker compose exec web sh
docker compose exec api sh
docker compose exec worker sh
```

## Variables relevantes

- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_PASSWORD`
- `BOOTSTRAP_ADMIN_NAME`
- `SESSION_COOKIE_NAME`
- `SESSION_TTL_MINUTES`
- `JWT_SECRET`

## Reglas operativas

- el frontend no debe contener credenciales hardcodeadas
- la autenticación se resuelve siempre desde backend
- cualquier cambio funcional debe actualizar documentación y pruebas
