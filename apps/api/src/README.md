# Estructura interna del backend

## `api/`

Versionado y definicion de endpoints.

## `core/`

Configuracion central, seguridad, logging y dependencias base.

## `db/`

Migraciones, seeds y configuracion de base de datos.

## `models/`

Modelos del dominio y de persistencia.

## `repositories/`

Capa de acceso a datos.

## `services/`

Logica de negocio por dominio:

- auth
- users
- chat
- retrieval
- manuals
- settings
- storage
- audit

## `tasks/` y `workers/`

Integracion con tareas asincronas y procesos de fondo iniciados desde la API.

## `tests/`

Pruebas unitarias e integracion del backend.
