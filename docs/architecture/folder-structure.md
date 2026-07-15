# Estructura de Carpetas

## Objetivo

Organizar el proyecto de forma que cualquier desarrollador pueda identificar rápidamente dónde vive cada responsabilidad al abrir el repositorio.

---

## Árbol principal

```text
rc7_programming_assistant/
├── apps/
│   ├── api/                    # Backend FastAPI
│   │   ├── src/
│   │   │   ├── api/v1/         # Endpoints versionados (routes, schemas, deps)
│   │   │   ├── core/           # Configuración y variables de entorno
│   │   │   ├── db/             # Sesión SQLAlchemy, modelos ORM e inicialización
│   │   │   └── services/       # Lógica de negocio por dominio (auth, chat, manuals)
│   │   └── tests/              # Pruebas del backend
│   ├── web/                    # Frontend Next.js
│   │   ├── src/
│   │   │   ├── app/            # Rutas y layouts (App Router)
│   │   │   ├── components/     # Componentes compartidos (layout, shared)
│   │   │   ├── features/       # Módulos funcionales (auth, chat, admin, settings)
│   │   │   ├── lib/            # Clientes HTTP y utilidades
│   │   │   └── styles/         # Tokens de diseño y estilos base
│   │   └── tests/              # Pruebas del frontend
│   └── worker/                 # Worker de ingestión documental
│       ├── src/
│       │   ├── core/           # Configuración del worker
│       │   ├── db/             # Sesión y modelos persistentes del pipeline
│       │   ├── jobs/           # Definición de trabajos ejecutables
│       │   ├── parsers/        # Extracción de texto desde PDFs
│       │   ├── chunking/       # Segmentación para retrieval
│       │   ├── services/       # Integraciones externas (MinIO)
│       │   └── utils/          # Utilidades del pipeline (logging)
│       └── tests/              # Pruebas del worker
├── packages/                   # Paquetes compartidos por api y worker (editable install)
│   ├── rc7_shared_config/      # SharedSettings: config común + validación de secretos
│   └── rc7_shared_db/          # Base ORM, modelos y migraciones compartidas
├── docs/                       # Documentación técnica
│   ├── architecture/           # Arquitectura y diseño
│   ├── audit/                  # Auditorías de código y doc-vs-código
│   ├── backend/                # Contratos API y módulos
│   ├── frontend/               # Layout y criterios de UX
│   ├── operations/             # Desarrollo local y testing
│   ├── rag/                    # Pipeline de ingestión
│   └── decisions/              # Architecture Decision Records
├── infra/                      # Infraestructura y contenedores
│   ├── docker/                 # Dockerfiles
│   ├── nginx/                  # Configuración de reverse proxy
│   ├── minio/                  # Notas de object storage (solo README)
│   └── postgres/               # Notas de la BD (solo README; el esquema lo crea la API al arrancar)
├── scripts/                    # Backup, export e import de datos
├── storage/                    # Volúmenes locales de desarrollo
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .env.prod.example
└── .gitignore
```

---

## Criterios de organización

### Versionado de la API — `apps/api/src/api/v1/`

Los endpoints se agrupan bajo un prefijo versionado (`/api/v1/`) para permitir la evolución de contratos sin romper integraciones existentes.

### Servicios de negocio — `apps/api/src/services/`

La lógica de negocio se aísla en servicios por dominio (`auth`, `chat`, `manuals`), manteniendo los endpoints como adaptadores delgados.

### Módulos funcionales del frontend — `apps/web/src/features/`

El código del frontend se agrupa por funcionalidad del producto (`auth`, `chat`, `admin`, `settings`), no por tipo técnico. Cada módulo exporta sus componentes a través de un barrel file (`index.ts`).

### Pruebas por aplicación — `apps/*/tests/`

Cada aplicación mantiene su suite automatizada en una carpeta `tests/` propia ubicada en la raíz del área (`api`, `web`, `worker`) para separar claramente código productivo y código de prueba.

### Documentación — `docs/`

Documentación técnica separada por dominio para evitar un README monolítico. Cada sección se mantiene junto con los cambios funcionales correspondientes.
