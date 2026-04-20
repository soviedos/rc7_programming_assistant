# Arquitectura General

## Resumen

La arquitectura del proyecto es un `monolito modular con frontend separado`, ejecutado completamente en contenedores. Esta base permite crecer hacia un asistente RAG especializado en PAC para DENSO RC7 sin introducir microservicios prematuros.

## Componentes actuales

### Frontend `apps/web`

Responsable de:

- login
- rutas protegidas
- workspace del asistente
- consola administrativa
- cambio de rol desde la sesión activa

### Backend `apps/api`

Responsable de:

- autenticación con correo y contraseña
- sesión por cookie firmada
- selección de rol activo
- endpoints base de administración y chat
- futura orquestación con Gemini y retrieval

### Worker `apps/worker`

Reservado para:

- ingestión documental
- parsing
- chunking
- embeddings
- reindexación

Hoy existe en modo placeholder, pero ya ocupa su lugar arquitectónico correcto.

### PostgreSQL + pgvector

Base transaccional principal y futura base vectorial. Actualmente ya soporta usuarios autorizados y autenticación.

### MinIO

Almacenamiento objetual para PDFs originales y derivados del pipeline documental.

### Redis

Coordinación de tareas asincrónicas y caché ligera.

## Flujo implementado hoy

1. El usuario accede al login.
2. El frontend envía credenciales al backend.
3. El backend valida el usuario activo en PostgreSQL.
4. Se emite una cookie de sesión HttpOnly.
5. El frontend consulta `/auth/me` para proteger rutas y resolver navegación.
6. El usuario puede cambiar de `admin` a `user` o viceversa si su perfil lo permite.

## Flujo objetivo RAG

1. Un administrador carga un manual PDF.
2. El backend registra el documento y delega al worker.
3. El worker parsea y clasifica por robot, controlador y tema.
4. PostgreSQL + pgvector guarda chunks y embeddings.
5. El backend recupera contexto filtrado.
6. Gemini responde con código PAC y referencias.

## Justificación global

Esta arquitectura prioriza:

- simplicidad operativa
- trazabilidad
- seguridad centralizada
- despliegue reproducible con Docker
- crecimiento gradual hacia RAG real
