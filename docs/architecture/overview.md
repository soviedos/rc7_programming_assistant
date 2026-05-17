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
| Tecnología | Python + SQLAlchemy + google-genai SDK |
| Responsabilidades | Ingestión documental completa: parsing con pypdf, chunking semántico, revisión y autocorrección con Gemini, generación de embeddings (`gemini-embedding-001`), indexación en pgvector |
| Estado | Completamente implementado y operativo |

### PostgreSQL + pgvector

Base de datos transaccional y vectorial. Soporta usuarios, autenticación, historial de chat, manuales, y chunks indexados con sus embeddings para búsqueda semántica.

### MinIO

Almacenamiento de objetos compatible con S3 para los PDFs originales de los manuales DENSO.

### Redis

Presente en el stack Docker. Actualmente sin consumidores activos; previsto para caché o colas en iteraciones futuras.

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

## Flujo RAG (implementado)

```text
1. Administrador carga un manual PDF → MinIO
2. Backend registra el documento; el worker lo reclama por polling a PostgreSQL
3. Worker descarga el PDF, extrae texto con pypdf y genera chunks semánticos
4. Gemini revisa y autocorrige cada chunk (revisión semántica)
5. Chunks se vectorizan con gemini-embedding-001 (dim. 768) y se indexan en pgvector
6. En el chat: usuario envía consulta + config del robot
7. Fase 1 (HyDE): Gemini genera respuesta hipotética a partir de la consulta
8. Embedding de (consulta + respuesta hipotética) → búsqueda vectorial en pgvector
9. Fase 2 (RAG): Gemini genera respuesta final con contexto de los chunks recuperados
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
