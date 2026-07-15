# RC7 Programming Assistant

> Asistente web especializado en programación PAC para robots DENSO con controlador RC7.
> Genera código PAC listo para copiar en WinCaps III, respaldado por un pipeline RAG
> de cuatro fases con HyDE y streaming SSE sobre manuales oficiales DENSO.

---

## Arquitectura

### Topología de servicios

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontFamily':'ui-sans-serif, system-ui','fontSize':'14px','lineColor':'#94a3b8'},'flowchart':{'curve':'basis','nodeSpacing':45,'rankSpacing':60}}}%%
flowchart TB
    Browser(["🌐 Browser"]):::client

    subgraph DockerStack["🐳 Docker Compose Stack"]
        Nginx["Nginx\n:80 / :443\nSSE: proxy_buffering off\nread_timeout 310s"]:::prod

        subgraph FE["apps/web — Next.js 16  ·  :3000"]
            NextJS["App Router · TypeScript · Tailwind\nSSE Consumer · Rutas protegidas por rol\nWorkspace PAC · Consola admin"]:::frontend
        end

        subgraph BE["apps/api — FastAPI  ·  :8000"]
            FastAPI["auth · profile · chat · manuals\nadmin · settings · audit\nJWT HttpOnly · SQLAlchemy · Pydantic v2"]:::backend
        end

        subgraph WK["apps/worker — Python 3.12"]
            Worker["Polling PostgreSQL cada ~5 s\nFOR UPDATE SKIP LOCKED\nMáx. 3 crash retries automáticos"]:::worker
        end

        subgraph DB["Persistencia"]
            PG[("PostgreSQL 17 + pgvector\n:5432\nusers · role_permissions · manuals · manual_chunks\nmanual_chunk_reviews · manual_review_summaries\nchat_history · audit_log · system_settings")]:::data
            MinIO[("MinIO\n:9000  /  :9001 console\nObject Storage S3-compatible\nPDFs originales")]:::data
        end
    end

    Gemini(["☁️ Google Gemini API\ngemini-3.5-flash\ngemini-embedding-2 (3072-dim)"]):::external

    Browser -->|HTTPS| Nginx
    Nginx -->|"proxy TODO (incl. /api/v1/*) → :3000"| NextJS
    NextJS -->|"proxy interno /api/v1/* → api:8000"| FastAPI
    FastAPI -->|"SQLAlchemy ORM"| PG
    FastAPI -->|"put_object / get_object (bytes vía API)"| MinIO
    FastAPI -->|"HyDE · SSE streaming"| Gemini
    PG -.->|"poll · reclama manual pendiente\nFOR UPDATE SKIP LOCKED"| Worker
    Worker -->|"download PDF"| MinIO
    Worker -->|"semantic review · embed_content"| Gemini
    Worker -->|"INSERT manual_chunks\nvector(3072) embeddings"| PG

    classDef client fill:#0f172a,stroke:#e2e8f0,stroke-width:2px,color:#f1f5f9
    classDef frontend fill:#0b3d5c,stroke:#38bdf8,stroke-width:2px,color:#e0f2fe
    classDef backend fill:#0f3d2e,stroke:#34d399,stroke-width:2px,color:#d1fae5
    classDef worker fill:#4a2f0a,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    classDef data fill:#2e1065,stroke:#a78bfa,stroke-width:2px,color:#ede9fe
    classDef external fill:#4a1535,stroke:#f472b6,stroke-width:2px,color:#fce7f3
    classDef prod fill:#1e293b,stroke:#94a3b8,stroke-width:2px,color:#cbd5e1,stroke-dasharray:5 3
    style DockerStack fill:#0b1220,stroke:#334155,color:#94a3b8
    style FE fill:#0c2a3f,stroke:#1e4e6b,color:#bae6fd
    style BE fill:#0b261c,stroke:#1f6f52,color:#86efac
    style WK fill:#2a1c08,stroke:#7a5a16,color:#fcd34d
    style DB fill:#160c2e,stroke:#5b3aa6,color:#c4b5fd
```

> **Nginx solo existe en producción** (`docker-compose.prod.yml`, TLS + reverse proxy).
> En el compose de **desarrollo** (`docker-compose.yml`) no hay nginx: el browser pega a
> `web:3000` y el proxy interno de Next.js reenvía `/api/v1/*` a `api:8000`.

### Pipelines — Ingestión y RAG

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontFamily':'ui-sans-serif, system-ui','fontSize':'14px','lineColor':'#94a3b8'},'flowchart':{'curve':'basis','nodeSpacing':40,'rankSpacing':45}}}%%
flowchart LR
    subgraph Ingest["⚙️  Pipeline de Ingestión  —  Worker"]
        direction TB
        I1(["Admin\nPOST /api/v1/manuals/"]):::io
        I2["MinIO upload PDF\nPostgreSQL  status = pending"]:::process
        I3["Worker\nFOR UPDATE SKIP LOCKED\nstatus = processing"]:::process
        I4["pypdf\nextract_pdf_text_by_page()"]:::process
        I5["build_text_chunks()\nchunking semántico"]:::process
        I6["GeminiSemanticReviewer\nrevisión de TODOS los chunks (sin muestreo)\ncoherence · completeness · boundary"]:::gemini
        I7["gemini-embedding-2\nbatch · 3072 dimensiones"]:::gemini
        I8[("manual_chunks\nstatus = indexed")]:::data

        I1 --> I2 --> I3 --> I4 --> I5 --> I6 --> I7 --> I8
    end

    subgraph RAG["💬  Pipeline RAG  —  POST /api/v1/chat/generate"]
        direction TB
        R1(["Usuario\nprompt + código PAC actual"]):::io
        R2["Fase 1 — HyDE\nGemini · respuesta hipotética\n(sin contexto documental)"]:::phase
        R3["Fase 2 — Retrieval\nembed(prompt + HyDE)\npgvector &lt;=&gt; (HNSW halfvec)\nre-rank por hardware + categoría · top-k"]:::data
        R4["Fase 3 — Contexto\nconstrucción con presupuesto de chars\nsource_map con IDs S1…Sn (trazabilidad)"]:::phase
        R5["Fase 4 — Respuesta final\nGemini + contexto RAG\nJSON: summary · pac_code · references (IDs citados)"]:::phase
        R6(["SSE Streaming\nevents: chunk → done\nkeepalive cada 15 s"]):::ok

        R1 --> R2 --> R3 --> R4 --> R5 --> R6
    end

    I8 --->|"similitud coseno\npgvector"| R3

    classDef io fill:#0f172a,stroke:#e2e8f0,stroke-width:2px,color:#f1f5f9
    classDef process fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#e2e8f0
    classDef gemini fill:#4a1535,stroke:#f472b6,stroke-width:2px,color:#fce7f3
    classDef data fill:#2e1065,stroke:#a78bfa,stroke-width:2px,color:#ede9fe
    classDef phase fill:#0b3d5c,stroke:#38bdf8,stroke-width:2px,color:#e0f2fe
    classDef ok fill:#052e16,stroke:#4ade80,stroke-width:2px,color:#dcfce7
    style Ingest fill:#160c04,stroke:#7a5a16,color:#fcd34d
    style RAG fill:#0c1f2e,stroke:#1e5a7a,color:#93c5fd
```

| Componente | Directorio | Responsabilidad |
|---|---|---|
| **Frontend** | `apps/web/` | Login, workspace del asistente, consola admin, SSE consumer |
| **Backend** | `apps/api/` | Auth JWT, RAG pipeline, SSE streaming, CRUD, audit |
| **Worker** | `apps/worker/` | Ingestión PDF: parse → chunk → revisión Gemini → embed → pgvector |
| **PostgreSQL + pgvector** | — | Datos transaccionales + almacenamiento vectorial |
| **MinIO** | — | PDFs originales (API compatible con S3) |
| **Nginx** | `infra/nginx/` | Reverse proxy; buffering desactivado para rutas SSE |

---

## Módulos de la API

| Módulo | Prefix | Descripción |
|---|---|---|
| `health` | `/api/v1/health` | Healthcheck |
| `auth` | `/api/v1/auth` | Login, sesión JWT HttpOnly, logout, switch-role |
| `profile` | `/api/v1/profile` | Perfil y contraseña del usuario autenticado |
| `chat` | `/api/v1/chat` | Pipeline RAG con SSE streaming, historial |
| `manuals` | `/api/v1/manuals` | CRUD de manuales + MinIO + trigger de ingestión + cancelación |
| `admin` | `/api/v1/admin` | Estado del sistema, usuarios, permisos de rol |
| `settings` | `/api/v1/admin/settings` | Parámetros configurables de Gemini/RAG en DB |
| `audit` | `/api/v1/admin/audit` | Registro inmutable de eventos del sistema |

---

## Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) >= 24.0
- [Docker Compose](https://docs.docker.com/compose/install/) >= 2.20
- Clave de API de Google Gemini ([obtener aquí](https://aistudio.google.com/))

Todo corre en Docker; no hace falta instalar Node ni Python en la máquina. Si aun
así se trabaja el frontend fuera de Docker, hay que usar **Node 22 / npm 10**, que
es lo que fija `infra/docker/web.Dockerfile`: npm 11+ resuelve los paquetes de
plataforma de forma distinta y rechaza el `package-lock.json` con "can only install
packages when your package.json and package-lock.json are in sync". En ese caso,
`npx npm@10.9.8 ci` instala respetando el lock.

---

## Inicio rápido

```bash
# 1. Clonar
git clone https://github.com/soviedos/rc7_programming_assistant.git
cd rc7_programming_assistant

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env: GEMINI_API_KEY, JWT_SECRET,
# BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD

# 3. Levantar el stack completo
docker compose up --build -d

# 4. Verificar servicios
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

---

## Variables de entorno

| Variable | Requerida | Default | Descripción |
|---|---|---|---|
| `APP_ENV` | No | `development` | Entorno (`development`, `production`) |
| `PROJECT_NAME` | No | `RC7 Programming Assistant API` | Nombre del proyecto (título en Swagger UI) |
| `BOOTSTRAP_ADMIN_EMAIL` | Sí | — | Email del admin inicial |
| `BOOTSTRAP_ADMIN_PASSWORD` | Sí | — | Contraseña del admin inicial |
| `BOOTSTRAP_ADMIN_NAME` | No | `Administrador RC7` | Nombre visible del admin inicial |
| `JWT_SECRET` | Sí | — | Secreto para firmar tokens JWT (mín. 32 chars) |
| `SESSION_COOKIE_NAME` | No | `rc7_session` | Nombre de la cookie de sesión |
| `SESSION_TTL_MINUTES` | No | `720` | Duración de la sesión (minutos) |
| `POSTGRES_HOST` | No | `postgres` | Host de PostgreSQL |
| `POSTGRES_PORT` | No | `5432` | Puerto de PostgreSQL |
| `POSTGRES_DB` | No | `rc7_assistant` | Nombre de la base de datos |
| `POSTGRES_USER` | No | `postgres` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | Sí* | `postgres` | Contraseña de PostgreSQL (*obligatoria en producción) |
| `MINIO_ENDPOINT` | No | `http://minio:9000` | Endpoint de MinIO |
| `MINIO_ROOT_USER` | No | `minioadmin` | Usuario root de MinIO |
| `MINIO_ROOT_PASSWORD` | Sí* | `minioadmin` | Contraseña root de MinIO (*obligatoria en producción) |
| `MINIO_BUCKET_MANUALS` | No | `rc7-manuals` | Bucket para almacenar PDFs |
| `GEMINI_API_KEY` | Sí | — | Clave de la API de Google Gemini |
| `ENABLE_STREAMING` | No | `true` | Activa SSE streaming en `/chat/generate` |
| `CORS_ORIGINS` | No | `["http://localhost:3000"]` | Orígenes permitidos en CORS |

> En `APP_ENV=production`, las variables marcadas con * y `JWT_SECRET` / `GEMINI_API_KEY`
> son validadas al arrancar — el proceso falla si contienen valores por defecto o débiles.

---

## Testing

```bash
# Backend (pytest, corre contra BD rc7_test auto-creada)
docker compose exec api python -m pytest

# Frontend (vitest). El contenedor `web` es el build de producción y no lleva
# devDependencies: los tests corren en el servicio `web-test`.
docker compose run --rm web-test

# Worker (pytest)
docker compose exec worker python -m pytest
```

---

## Estructura del repositorio

```text
rc7_programming_assistant/
├── .github/
│   └── workflows/    # CI/CD (deploy.yml)
├── apps/
│   ├── api/          # Backend FastAPI (Python 3.12)
│   ├── web/          # Frontend Next.js 16
│   └── worker/       # Worker de ingestión documental
├── packages/
│   ├── rc7_shared_config/ # SharedSettings: config común + validación de secretos (api y worker)
│   └── rc7_shared_db/     # Modelos ORM, Base y migraciones compartidas (api y worker)
├── docs/             # Documentación técnica
│   ├── architecture/ # Visión general, decisiones, diagramas Mermaid (ARCHITECTURE.md)
│   ├── backend/      # Módulos API: endpoints, settings, audit
│   ├── frontend/     # Layout y criterios de UX
│   ├── operations/   # Desarrollo local, testing, despliegue
│   ├── rag/          # Pipeline de ingestión documental
│   ├── audit/        # Auditoría de código y divergencias doc-vs-código
│   └── decisions/    # Architecture Decision Records (ADR)
├── infra/            # Dockerfiles y configuración de servicios
├── logs/             # Logs de api y worker (excluidos del control de versiones)
├── scripts/          # Scripts de backup y migración de datos
├── storage/          # Volúmenes locales (desarrollo)
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example      # Template de variables para desarrollo
└── .env.prod.example # Template de variables para producción
```

---

## Documentación

| Documento | Descripción |
|---|---|
| [Arquitectura (diagramas Mermaid)](./docs/architecture/ARCHITECTURE.md) | Componentes, ingestión, RAG, vectorial, auth, secuencias y ER |
| [Arquitectura general](./docs/architecture/overview.md) | Componentes, flujos RAG, audit y settings |
| [Auditoría de código](./docs/audit/CODE_AUDIT.md) | Hallazgos por severidad, limpiezas y propuestas |
| [Documentación vs. código](./docs/audit/DOC_VS_CODE.md) | Tabla de divergencias verificadas/corregidas |
| [Decisiones tecnológicas](./docs/architecture/technology-decisions.md) | ADRs: pgvector, HyDE, SSE, settings en DB |
| [Módulos del backend](./docs/backend/api-modules.md) | Tabla completa de endpoints |
| [Módulo settings](./docs/backend/settings-module.md) | Parámetros configurables y su efecto |
| [Módulo audit](./docs/backend/audit-module.md) | Eventos registrados y API de consulta |
| [Ingestión de manuales](./docs/rag/manual-ingestion.md) | Pipeline worker: parse → chunk → embed |
| [Estructura de carpetas](./docs/architecture/folder-structure.md) | Organización del repositorio |
| [Desarrollo local](./docs/operations/local-development.md) | Guía de arranque y operación |
| [Despliegue en producción](./docs/operations/deployment.md) | Configuración y migración de datos |
| [Testing](./docs/operations/testing.md) | Estrategia y comandos de prueba |

---

## Tecnologías principales

| Capa | Tecnología | Versión mínima |
|---|---|---|
| Frontend | Next.js + React + TypeScript | 16 (`next@16.2.4`, React 19) |
| Backend | FastAPI + SQLAlchemy + Pydantic v2 | Python 3.12+ |
| Worker | Python + google-genai SDK + pypdf | Python 3.12+ |
| Base de datos | PostgreSQL + pgvector (`vector(3072)` · HNSW) | 17+ |
| Object storage | MinIO (S3-compatible) | — |
| Contenedores | Docker + Docker Compose | 24.0+ / 2.20+ |
| IA | Google Gemini 3.5 Flash + gemini-embedding-2 (3072-dim) | — |
| Testing | pytest, Vitest | — |

---

## Licencia

Este proyecto está licenciado bajo [Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](./LICENSE).

Puedes estudiar y compartir el código con atribución, pero **no está permitido su uso comercial** sin autorización expresa del autor.

© 2026 Sergio Oviedo Seas
