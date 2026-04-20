# Testing

## Objetivo

Validar automáticamente el comportamiento que ya está implementado hoy, sin simular cobertura sobre módulos todavía no construidos.

## Backend `apps/api`

Se usa `pytest` para validar:

- login
- sesión actual
- cambio de rol
- logout
- root
- healthcheck
- chat placeholder
- admin status placeholder
- utilidades de password, roles y tokens

Las pruebas usan SQLite temporal y overrides de dependencias de FastAPI.

## Frontend `apps/web`

Se usa `Vitest + Testing Library` para validar:

- formulario de login
- validación amigable
- limpieza del formulario al fallar
- mostrar u ocultar contraseña
- redirect por rol
- perfil de sesión
- protección de rutas
- normalización de errores del API

## Worker `apps/worker`

Se validan:

- logging base
- ciclo placeholder del worker

## Comandos

### Backend

```bash
docker compose exec api python -m pytest
```

### Frontend

```bash
docker compose exec web npm test
```

### Worker

```bash
docker compose exec worker python -m pytest
```
