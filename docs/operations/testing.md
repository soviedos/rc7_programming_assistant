# Testing

## Estrategia

Las pruebas automatizadas validan exclusivamente el comportamiento implementado. No se simula cobertura sobre módulos que aún no existen.

---

## Backend — `apps/api/`

**Framework**: pytest

**Cobertura actual**:

| Área | Pruebas |
|---|---|
| Autenticación | Login, sesión actual, cambio de rol, logout |
| Rutas base | Root (`/`), healthcheck |
| Contratos placeholder | Chat generate, admin status |
| Utilidades | Hashing de passwords, validación de roles, generación de tokens |

**Entorno de pruebas**: SQLite en memoria con overrides de dependencias de FastAPI.

```bash
docker compose exec api python -m pytest
```

---

## Frontend — `apps/web/`

**Framework**: Vitest + Testing Library

**Cobertura actual**:

| Área | Pruebas |
|---|---|
| Login | Formulario, validación amigable, limpieza al fallar, mostrar/ocultar contraseña |
| Navegación | Redirect por rol, protección de rutas |
| Sesión | Perfil de sesión, resolución de usuario actual |
| Errores | Normalización de errores de la API |

```bash
docker compose exec web npm test
```

---

## Worker — `apps/worker/`

**Framework**: pytest

**Cobertura actual**:

| Área | Pruebas |
|---|---|
| Logging | Configuración base del sistema de logs |
| Worker loop | Ciclo placeholder de ejecución |

```bash
docker compose exec worker python -m pytest
```

---

## Ejecución completa

Para ejecutar todas las suites desde la raíz del proyecto:

```bash
docker compose exec api python -m pytest
docker compose exec web npm test
docker compose exec worker python -m pytest
```
