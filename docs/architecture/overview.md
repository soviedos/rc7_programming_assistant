# Arquitectura General

## Resumen

El proyecto implementa una arquitectura de **monolito modular con frontend separado**, ejecutado completamente en contenedores Docker. Este diseño permite evolucionar hacia un asistente RAG especializado en programación PAC para DENSO RC7 sin introducir la complejidad de microservicios prematuros.

---

## Componentes

### Frontend — `apps/web/`

| Aspecto | Detalle |
|---|---|
| Tecnología | Next.js + React + TypeScript |
| Puerto | 3000 |
| Responsabilidades | Login, rutas protegidas, workspace del asistente, consola administrativa, cambio de rol |

### Backend — `apps/api/`

| Aspecto | Detalle |
|---|---|
| Tecnología | FastAPI + SQLAlchemy + Pydantic |
| Puerto | 8000 |
| Responsabilidades | Autenticación, sesión por cookie firmada, selección de rol activo, endpoints de administración y chat, futura orquestación con Gemini y retrieval |

### Worker — `apps/worker/`

| Aspecto | Detalle |
|---|---|
| Tecnología | Python + Redis |
| Responsabilidades | Ingestión documental, parsing, chunking, embeddings, indexación |
| Estado | Placeholder funcional; ocupa su lugar arquitectónico para el pipeline RAG |

### PostgreSQL + pgvector

Base de datos transaccional principal y futura base vectorial. Actualmente soporta la persistencia de usuarios autorizados y la autenticación del sistema.

### MinIO

Almacenamiento de objetos compatible con S3 para PDFs originales y derivados del pipeline documental.

### Redis

Coordinación de tareas asincrónicas entre el backend y el worker, y caché ligera de operaciones frecuentes.

---

## Flujo de autenticación (implementado)

```text
1. Usuario accede al login (/)
2. Frontend envía credenciales → POST /api/v1/auth/login
3. Backend valida usuario activo en PostgreSQL
4. Se emite cookie de sesión HttpOnly con JWT firmado
5. Frontend consulta GET /api/v1/auth/me para proteger rutas
6. Usuario puede cambiar rol (admin ↔ user) si su perfil lo permite
```

## Flujo RAG (objetivo)

```text
1. Administrador carga un manual PDF → MinIO
2. Backend registra el documento y delega al worker vía Redis
3. Worker parsea, clasifica por robot/controlador y genera chunks
4. Chunks + embeddings se indexan en PostgreSQL + pgvector
5. Backend recupera contexto filtrado por configuración del robot
6. Gemini genera respuesta con código PAC y referencias citadas
```

---

## Principios de diseño

| Principio | Justificación |
|---|---|
| **Simplicidad operativa** | Un solo `docker compose up` levanta todo el sistema |
| **Trazabilidad** | Cada acción pasa por el backend, facilitando auditoría |
| **Seguridad centralizada** | Autenticación y autorización resueltas exclusivamente en el backend |
| **Despliegue reproducible** | Contenedores con healthchecks y dependencias declarativas |
| **Crecimiento gradual** | La estructura soporta RAG real sin refactoring arquitectónico |
