# Decisiones Tecnológicas

Resumen de las tecnologías seleccionadas para el proyecto y la justificación detrás de cada elección.

---

## Frontend — Next.js

| Criterio | Detalle |
|---|---|
| **Rutas y layouts** | App Router permite definir rutas protegidas, layouts anidados y separación clara entre landing, workspace y administración |
| **TypeScript** | Integración nativa con tipado estático |
| **Ecosistema** | Soporte amplio de componentes, testing y herramientas de desarrollo |
| **Experiencia de desarrollo** | Hot reload, integración con VS Code y debugging integrado |

## Backend — FastAPI

| Criterio | Detalle |
|---|---|
| **Rendimiento** | Framework asincrónico de alto rendimiento sobre Python |
| **Tipado y validación** | Pydantic integrado para validación automática de request/response |
| **Documentación** | Swagger UI y ReDoc generados automáticamente |
| **Ecosistema IA** | Compatibilidad directa con librerías de ML, embeddings y SDKs de LLMs |

## Worker — Python independiente

| Criterio | Detalle |
|---|---|
| **Aislamiento** | Proceso separado para parsing y chunking pesado, sin bloquear requests HTTP |
| **Reindexación** | Capacidad de reprocesar documentos completos sin afectar la API |
| **Coordinación** | Comunicación con el backend a través de Redis como broker de tareas |

## Base de datos — PostgreSQL + pgvector

| Criterio | Detalle |
|---|---|
| **Unificación** | Una sola base para datos transaccionales y almacenamiento vectorial |
| **Complejidad operativa** | Menor carga operativa que mantener bases separadas (e.g., Pinecone, Weaviate) |
| **Volumen** | Adecuado para el volumen inicial de manuales DENSO |

## Object storage — MinIO

| Criterio | Detalle |
|---|---|
| **Compatibilidad** | API compatible con S3, facilitando migración futura a AWS/GCP |
| **Despliegue local** | Contenedor ligero sin dependencia de proveedores cloud |
| **Independencia** | Almacenamiento desacoplado del sistema de archivos del host |

## Cache y colas — Redis

| Criterio | Detalle |
|---|---|
| **Versatilidad** | Soporta colas de tareas, cache y pub/sub en un solo servicio |
| **Ecosistema** | Adopción amplia con clientes maduros en Python y Node.js |
| **Simplicidad** | Configuración mínima para el stack de desarrollo local |
