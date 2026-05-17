# RC7 Programming Assistant

> Asistente web especializado en programación PAC para robots DENSO con controlador RC7.  
> Genera respuestas técnicas y código listo para copiar en WinCaps III, respaldado por Retrieval-Augmented Generation (RAG) sobre manuales oficiales DENSO.

---

## Descripción

RC7 Programming Assistant es una plataforma web que combina un backend de autenticación y orquestación, un frontend orientado a ingeniería y un pipeline de procesamiento documental para ofrecer asistencia contextualizada en programación PAC, troubleshooting y configuración de robots DENSO RC7.

### Objetivos principales

| Objetivo | Descripción |
|---|---|
| **Asistencia técnica PAC** | Generación de código PAC con referencias a manuales oficiales |
| **Autenticación segura** | Sesiones persistentes con JWT en cookies HttpOnly |
| **Administración centralizada** | Gestión de usuarios, parámetros del modelo y base documental |
| **RAG especializado** | Recuperación de contexto filtrado por robot, controlador y versión |
| **Despliegue reproducible** | Stack completo orquestado con Docker Compose |

---

## Arquitectura

El proyecto sigue una arquitectura de **monolito modular con frontend separado**, diseñada para mantener la simplicidad operativa sin sacrificar la separación de responsabilidades.

```text
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend   │────▶│   Backend   │────▶│   Worker    │
│   Next.js    │     │   FastAPI   │     │   Python    │
│  :3000       │     │  :8000      │     │             │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                    │
                    ┌──────┴──────┐      ┌──────┴──────┐
                    │  PostgreSQL │      │    MinIO     │
                    │  + pgvector │      │  (S3-compat) │
                    │  :5432      │      │  :9000       │
                    └─────────────┘      └─────────────┘
                           │
                    ┌──────┴──────┐
                    │    Redis    │
                    │  :6379      │
                    └─────────────┘
```

| Componente | Directorio | Responsabilidad |
|---|---|---|
| **Frontend** | `apps/web/` | Interfaz de usuario, rutas protegidas, workspace del asistente |
| **Backend** | `apps/api/` | Autenticación, contratos HTTP, orquestación de servicios |
| **Worker** | `apps/worker/` | Pipeline de ingestión documental y generación de embeddings |
| **PostgreSQL + pgvector** | — | Datos transaccionales y almacenamiento vectorial |
| **MinIO** | — | Almacenamiento de PDFs originales (compatible con S3) |
| **Redis** | — | Coordinación de tareas asincrónicas y caché |

> Para detalles arquitectónicos, consulte [docs/architecture/overview.md](./docs/architecture/overview.md).

---

## Estructura del repositorio

```text
rc7_programming_assistant/
├── apps/
│   ├── api/          # Backend FastAPI
│   ├── web/          # Frontend Next.js
│   └── worker/       # Worker de ingestión documental
├── docs/             # Documentación técnica del proyecto
│   ├── architecture/ # Arquitectura y decisiones de diseño
│   ├── backend/      # Contratos API y módulos
│   ├── frontend/     # Layout y criterios de UX
│   ├── operations/   # Desarrollo local y testing
│   ├── rag/          # Pipeline de ingestión documental
│   └── decisions/    # Architecture Decision Records (ADR)
├── infra/            # Dockerfiles y configuración de servicios
│   ├── docker/
│   ├── nginx/
│   ├── minio/
│   ├── postgres/
│   └── redis/
├── scripts/          # Scripts de migración y mantenimiento de datos
├── storage/          # Volúmenes locales para desarrollo
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── .env.prod.example  # Template de variables para producción
```

---

## Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) >= 24.0
- [Docker Compose](https://docs.docker.com/compose/install/) >= 2.20
- Archivo `.env` configurado (ver sección de configuración)

---

## Inicio rápido

### 1. Clonar el repositorio

```bash
git clone https://github.com/soviedos/rc7_programming_assistant.git
cd rc7_programming_assistant
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Edite `.env` y configure al menos las siguientes variables:

```env
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=<contraseña-segura>
JWT_SECRET=<secreto-aleatorio>
```

### 3. Levantar el stack

```bash
docker compose up --build -d
```

### 4. Verificar servicios

```bash
docker compose ps
curl -s http://localhost:8000/api/v1/health/ | python3 -m json.tool
```

---

## Servicios expuestos

| Servicio | URL | Descripción |
|---|---|---|
| Frontend | http://localhost:3000 | Interfaz web principal |
| API | http://localhost:8000 | Backend REST |
| Swagger UI | http://localhost:8000/docs | Documentación interactiva de la API |
| MinIO Console | http://localhost:9001 | Administración de object storage |
| PostgreSQL | localhost:5432 | Base de datos (acceso directo) |
| Redis | localhost:6379 | Cache y colas (acceso directo) |

---

## Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/health/` | Healthcheck del servicio |
| `POST` | `/api/v1/auth/login` | Inicio de sesión |
| `GET` | `/api/v1/auth/me` | Sesión actual del usuario |
| `POST` | `/api/v1/auth/switch-role` | Cambio de rol activo |
| `POST` | `/api/v1/auth/logout` | Cierre de sesión |
| `GET` | `/api/v1/admin/status` | Estado administrativo |
| `GET` | `/api/v1/manuals` | Listado de manuales registrados |
| `GET` | `/api/v1/manuals/{id}` | Detalle de un manual |
| `POST` | `/api/v1/manuals` | Carga de un manual PDF |
| `POST` | `/api/v1/chat/generate` | Generación de respuesta del asistente |

> Documentación completa disponible en [Swagger UI](http://localhost:8000/docs) con el stack en ejecución.

---

## Testing

Todas las suites de prueba se ejecutan dentro de los contenedores:

- Backend: `apps/api/tests/`
- Frontend: `apps/web/tests/`
- Worker: `apps/worker/tests/`

```bash
# Backend (pytest)
docker compose exec api python -m pytest

# Frontend (vitest)
docker compose exec web npm test

# Worker (pytest)
docker compose exec worker python -m pytest
```

> Para detalles sobre la estrategia de testing, consulte [docs/operations/testing.md](./docs/operations/testing.md).

---

## Estado del proyecto

### Implementado

- Autenticación completa con sesión por cookie HttpOnly y JWT
- Bootstrap de administrador por variables de entorno
- Frontend con login, workspace del asistente y consola administrativa
- Stack contenedorizado con healthchecks y dependencias gestionadas
- Suite de pruebas automatizadas (backend, frontend, worker)
- Integración con Google Gemini (pipeline RAG con HyDE en dos fases)
- Pipeline de ingestión de manuales PDF (parsing → chunking → revisión semántica → embeddings → pgvector)
- Búsqueda vectorial con pgvector integrada en el chat
- CRUD administrativo completo de usuarios y manuales
- Configuración de producción (Dockerfiles optimizados, `docker-compose.prod.yml`, Nginx, scripts de migración)

### Pendiente

- Autenticación con Google SSO
- Módulo de auditoría de acciones administrativas

> Consulte [docs/operations/scaffold-status.md](./docs/operations/scaffold-status.md) para el estado detallado.

---

## Documentación

| Documento | Descripción |
|---|---|
| [Arquitectura general](./docs/architecture/overview.md) | Componentes, flujos y justificación técnica |
| [Estructura de carpetas](./docs/architecture/folder-structure.md) | Organización del repositorio |
| [Decisiones tecnológicas](./docs/architecture/technology-decisions.md) | Justificación de cada tecnología |
| [Módulos del backend](./docs/backend/api-modules.md) | Endpoints y servicios implementados |
| [Layout del workspace](./docs/frontend/workspace-layout.md) | Diseño de la interfaz principal |
| [Desarrollo local](./docs/operations/local-development.md) | Guía de arranque y operación |
| [Despliegue en producción](./docs/operations/deployment.md) | Configuración y migración de datos |
| [Testing](./docs/operations/testing.md) | Estrategia y comandos de prueba |
| [Ingestión de manuales](./docs/rag/manual-ingestion.md) | Pipeline RAG implementado |
| [ADR-0001](./docs/decisions/ADR-0001-monolithic-modular-architecture.md) | Decisión de arquitectura modular |

---

## Tecnologías principales

| Capa | Tecnología | Versión mínima |
|---|---|---|
| Frontend | Next.js + React + TypeScript | latest |
| Backend | FastAPI + SQLAlchemy + Pydantic | Python 3.12+ |
| Worker | Python + Redis | Python 3.12+ |
| Base de datos | PostgreSQL + pgvector | 15+ |
| Object storage | MinIO (S3-compatible) | — |
| Cache / Colas | Redis | 7+ |
| Contenedores | Docker + Docker Compose | 24.0+ / 2.20+ |
| Testing | pytest, Vitest, Testing Library | — |

---

## Licencia

Proyecto privado. Todos los derechos reservados.
