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
│   │   │   ├── api/v1/         # Endpoints versionados (routes, schemas)
│   │   │   ├── core/           # Configuración, seguridad, dependencias base
│   │   │   ├── db/             # Migraciones, seeds, sesión de base de datos
│   │   │   ├── models/         # Modelos de dominio y persistencia
│   │   │   ├── repositories/   # Capa de acceso a datos
│   │   │   ├── services/       # Lógica de negocio por dominio
│   │   │   ├── tasks/          # Tareas asincrónicas
│   │   │   └── workers/        # Procesos de fondo iniciados desde la API
│   │   └── tests/              # Pruebas del backend
│   ├── web/                    # Frontend Next.js
│   │   └── src/
│   │       ├── app/            # Rutas y layouts (App Router)
│   │       ├── components/     # Componentes reutilizables
│   │       ├── features/       # Módulos funcionales por dominio
│   │       ├── lib/            # Clientes HTTP y utilidades
│   │       ├── styles/         # Estilos globales
│   │       └── types/          # Tipos TypeScript compartidos
│   └── worker/                 # Worker de ingestión documental
│       ├── src/
│       │   ├── jobs/           # Definición de trabajos ejecutables
│       │   ├── parsers/        # Extracción de texto desde PDFs
│       │   ├── chunking/       # Segmentación para retrieval
│       │   ├── classifiers/    # Detección de aplicabilidad técnica
│       │   ├── embeddings/     # Generación de vectores
│       │   ├── indexing/       # Carga en PostgreSQL + pgvector
│       │   └── utils/          # Utilidades del pipeline
│       └── tests/              # Pruebas del worker
├── docs/                       # Documentación técnica
│   ├── architecture/           # Arquitectura y diseño
│   ├── backend/                # Contratos API y módulos
│   ├── frontend/               # Layout y criterios de UX
│   ├── operations/             # Desarrollo local y testing
│   ├── rag/                    # Pipeline de ingestión
│   └── decisions/              # Architecture Decision Records
├── infra/                      # Infraestructura y contenedores
│   ├── docker/                 # Dockerfiles
│   ├── nginx/                  # Configuración de reverse proxy
│   ├── minio/                  # Configuración de object storage
│   ├── postgres/               # Scripts de inicialización de BD
│   └── redis/                  # Configuración de cache y colas
├── storage/                    # Volúmenes locales de desarrollo
├── docker-compose.yml
├── .env.example
└── .gitignore
```

---

## Criterios de organización

### Versionado de la API — `apps/api/src/api/v1/`

Los endpoints se agrupan bajo un prefijo versionado (`/api/v1/`) para permitir la evolución de contratos sin romper integraciones existentes.

### Servicios de negocio — `apps/api/src/services/`

La lógica de negocio se aísla en servicios por dominio (`auth`, `chat`, `users`, `retrieval`, etc.), manteniendo los endpoints como adaptadores delgados.

### Repositorios — `apps/api/src/repositories/`

El acceso a datos se encapsula en repositorios, desacoplando el dominio de los detalles de persistencia.

### Módulos funcionales del frontend — `apps/web/src/features/`

El código del frontend se agrupa por funcionalidad del producto (autenticación, workspace, historial), no por tipo técnico.

### Clasificadores del worker — `apps/worker/src/classifiers/`

Módulo dedicado a detectar la aplicabilidad técnica de cada chunk (tipo de robot, número de ejes, versión del controlador). Esta carpeta existe porque el filtrado por contexto técnico es central en el producto.

### Documentación — `docs/`

Documentación técnica separada por dominio para evitar un README monolítico. Cada sección se mantiene junto con los cambios funcionales correspondientes.
