# Testing

## Estrategia

Las pruebas automatizadas validan exclusivamente el comportamiento implementado. No se simula cobertura sobre módulos que aún no existen.

Todas las suites se ejecutan dentro de Docker usando `docker compose exec ...`.

---

## Backend — `apps/api/`

**Framework**: pytest

**Ubicación de pruebas**: `apps/api/tests/`

**Cobertura actual**:

| Área | Pruebas |
|---|---|
| Autenticación | Login, sesión actual, cambio de rol, logout |
| Rutas base | Root (`/`), healthcheck |
| Chat streaming | Pipeline RAG completo con SSE, errores y autenticación |
| Chat retrieval | Búsqueda vectorial pgvector (`<=>`), re-rank por categoría y por **compatibilidad de hardware** (`test_chat_retrieval.py`) |
| Chat trazabilidad | Resolución de IDs de fuente `S1…Sn`, descarte de IDs alucinados, prompt de trazabilidad (`test_chat_traceability.py`) |
| Utilidades | Hashing de passwords, validación de roles, generación de tokens |
| Admin usuarios | CRUD, permisos por rol, validación de restricciones |
| Manuales | Carga, listado, eliminación, retry, cancelación |
| Auditoría | Creación de registros, filtros, paginación |
| Profile | Lectura/escritura de perfil, cambio de contraseña |
| Settings | CRUD completo de parámetros del sistema |

**Entorno de pruebas**: base PostgreSQL dedicada `rc7_test`, auto-creada por el fixture de
conftest con la extensión `vector` habilitada (necesaria para la columna `vector(3072)`), más
overrides de dependencias de FastAPI.

**Helpers compartidos**: `apps/api/tests/helpers.py` contiene `create_user()` y `login()` usados por todos los módulos de prueba para evitar duplicación.

```bash
docker compose exec api python -m pytest
```

---

## Frontend — `apps/web/`

**Framework**: Vitest + Testing Library

**Ubicación de pruebas**: `apps/web/tests/`

**Cobertura actual** (47 tests, 11 archivos):

| Área | Pruebas |
|---|---|
| Login | Formulario, validación amigable, limpieza al fallar, mostrar/ocultar contraseña |
| Navegación | Redirect por rol, protección de rutas |
| Sesión | Perfil de sesión, menú de usuario, resolución de rol activo |
| Manuales | Modal de carga, extracción automática de metadatos desde PDF, envío |
| Perfil | Validación de contraseñas, helpers de perfil |
| API client | Normalización de errores, funciones de autenticación |

El contenedor `web` sirve el build standalone de producción y no incluye
devDependencies, así que vitest no vive ahí. La suite corre en el servicio
`web-test` (etapa `test` de `infra/docker/web.Dockerfile`), que está bajo el
perfil `test` y por eso no arranca con `docker compose up`:

```bash
docker compose run --rm web-test
```

---

## Worker — `apps/worker/`

**Framework**: pytest

**Ubicación de pruebas**: `apps/worker/tests/`

**Cobertura actual**:

| Área | Pruebas |
|---|---|
| Logging | Configuración base del sistema de logs |
| Ingestión | Ciclo completo de ingestión con chunking, manejo de fallos y heartbeat |
| Chunking | Segmentación de texto por tamaño máximo |
| Revisión semántica | Selección de chunks, elegibilidad por idioma/título, métricas agregadas |

**Entorno de pruebas**: SQLite por test (el tipo `EmbeddingVector` cae a JSON fuera de PostgreSQL).

```bash
docker compose exec worker python -m pytest
```

---

## Ejecución completa

Para ejecutar todas las suites desde la raíz del proyecto:

```bash
docker compose exec api python -m pytest
docker compose run --rm web-test
docker compose exec worker python -m pytest
```

Si los contenedores no están levantados, primero ejecute:

```bash
docker compose up --build -d
```
