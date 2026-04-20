# Módulos del Backend

## Implementados hoy

### `auth`

Gestiona:

- login con correo y contraseña
- sesión actual
- cambio de rol
- logout
- firma y lectura de cookie de sesión

### `health`

Healthcheck para diagnóstico y Docker.

### `chat`

Expone un contrato placeholder con:

- resumen
- código PAC
- referencias

### `admin`

Expone un estado administrativo placeholder para sostener la UI y el contrato inicial.

## Implementados parcialmente

### `users`

Existe el modelo `User` y la persistencia real para autenticación, pero todavía falta CRUD administrativo completo.

## Pendientes planificados

### `manuals`

- carga de PDFs
- versionado
- metadatos por robot y controlador

### `retrieval`

- búsqueda vectorial en pgvector
- filtros de aplicabilidad técnica
- citación por página y sección

### `settings`

- parámetros de Gemini
- prompts del sistema
- políticas de respuesta

### `audit`

- acciones administrativas
- cambios de configuración
- eventos de ingestión
