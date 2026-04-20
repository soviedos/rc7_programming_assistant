# Estructura interna del backend

Organización del código fuente del backend por capas de responsabilidad.

---

## Directorio `api/`

Endpoints HTTP versionados. Cada versión (`v1/`) contiene sus rutas (`routes/`) y esquemas de validación (`schemas/`).

## Directorio `core/`

Configuración central del sistema: variables de entorno, seguridad, logging y dependencias base compartidas por todos los módulos.

## Directorio `db/`

Gestión de la base de datos: sesión de SQLAlchemy, migraciones, seeds de datos iniciales y scripts de inicialización.

## Directorio `models/`

Modelos de dominio y de persistencia (entidades SQLAlchemy).

## Directorio `repositories/`

Capa de acceso a datos. Encapsula las consultas a la base de datos y mantiene la lógica de negocio desacoplada de los detalles de persistencia.

## Directorio `services/`

Lógica de negocio organizada por dominio:

| Servicio | Responsabilidad |
|---|---|
| `auth/` | Autenticación, sesiones y gestión de contraseñas |
| `users/` | Gestión de usuarios y perfiles |
| `chat/` | Orquestación de respuestas del asistente |
| `retrieval/` | Búsqueda vectorial y recuperación de contexto |
| `manuals/` | Gestión de la base documental |
| `settings/` | Configuración administrativa del sistema |
| `storage/` | Interacción con MinIO (object storage) |
| `audit/` | Registro de eventos y acciones |

## Directorio `tasks/` y `workers/`

Integración con tareas asincrónicas y procesos de fondo iniciados desde la API hacia el worker.

## Directorio `tests/`

Pruebas unitarias y de integración del backend.
