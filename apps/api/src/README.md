# Estructura interna del backend

Organización del código fuente del backend por capas de responsabilidad.

---

## Directorio `api/`

Endpoints HTTP versionados. Cada versión (`v1/`) contiene sus rutas (`routes/`) y esquemas de validación (`schemas/`).

## Directorio `core/`

Configuración central del sistema: variables de entorno, seguridad, logging y dependencias base compartidas por todos los módulos.

## Directorio `db/`

Gestión de la base de datos: sesión de SQLAlchemy, modelos ORM (`models/`) y scripts de inicialización (bootstrap de tablas y admin).

## Directorio `services/`

Lógica de negocio organizada por dominio:

| Servicio | Responsabilidad |
|---|---|
| `auth/` | Autenticación, sesiones y gestión de contraseñas |
| `chat/` | Orquestación de respuestas del asistente (placeholder) |
| `manuals/` | Gestión de la base documental y storage en MinIO |

## Directorio `tests/`

Pruebas unitarias y de integración del backend.
