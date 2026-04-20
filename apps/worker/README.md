# Worker — Pipeline de ingestión documental

Proceso asincrónico del RC7 Programming Assistant, dedicado al procesamiento de manuales PDF para el pipeline RAG.

---

## Stack técnico

| Tecnología | Uso |
|---|---|
| Python 3.12+ | Runtime |
| SQLAlchemy + psycopg | Acceso a PostgreSQL |
| MinIO SDK | Descarga de manuales PDF |
| pypdf | Extracción inicial de texto |
| Redis | Coordinación de tareas con el backend |
| pydantic-settings | Configuración por variables de entorno |

---

## Estado actual

El worker ya ejecuta una primera versión funcional del pipeline:

- Detecta manuales con estado `pending`
- Los marca como `processing`
- Descarga el PDF desde MinIO
- Extrae texto por página
- Genera chunks textuales iniciales
- Persiste los chunks en PostgreSQL
- Marca el manual como `indexed` o `failed`

## Responsabilidades objetivo

| Etapa | Descripción |
|---|---|
| **Parsing** | Extracción de texto y estructura desde PDFs |
| **Chunking** | Segmentación del contenido en unidades recuperables |
| **Clasificación** | Detección de aplicabilidad por robot, ejes y versión |
| **Embeddings** | Generación de vectores para búsqueda semántica |
| **Indexación** | Carga de chunks y vectores en PostgreSQL + pgvector |

## Siguiente iteración natural

- Clasificación técnica por robot/controlador
- Embeddings por chunk
- Indexación vectorial con pgvector
- Disparo explícito de jobs desde backend/Redis en lugar de polling simple

---

## Pruebas

```bash
docker compose exec worker python -m pytest
```
