# Estructura interna del backend

Organización del código fuente del backend por capas de responsabilidad.

---

## Directorio `api/`

Endpoints HTTP versionados. Cada versión (`v1/`) contiene sus rutas (`routes/`) y esquemas de validación (`schemas/`).

## Directorio `core/`

Configuración central del sistema: variables de entorno (`config.py`) y logging
(`logging.py`). La seguridad vive en `services/auth/` y las dependencias inyectables en
`api/v1/deps/`.

## Directorio `db/`

Gestión de la base de datos: sesión de SQLAlchemy, modelos ORM (`models/`) y scripts de inicialización (bootstrap de tablas y admin).

## Directorio `services/`

Lógica de negocio organizada por dominio:

| Servicio | Responsabilidad |
|---|---|
| `auth/` | Autenticación, sesiones y gestión de contraseñas |
| `chat/` | Pipeline RAG de 4 fases (HyDE → embedding → retrieval pgvector → generación Gemini), streaming SSE, linter PAC determinista, advisories y trazabilidad de fuentes |
| `manuals/` | Gestión de la base documental y storage en MinIO |
| `settings/` | Catálogo `DEFAULT_SETTINGS`, CRUD, seed y migraciones dirigidas de parámetros |
| `audit_service.py` | Registro de eventos (`log_event`, `get_audit_logs`). Nunca lanza excepción |

## Pruebas

`tests/` **no** está dentro de `src/`: es hermano suyo, en `apps/api/tests/`. Contiene las
pruebas unitarias y de integración del backend.
