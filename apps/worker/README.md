# Worker — Pipeline de ingestión documental

Proceso asincrónico del RC7 Programming Assistant, dedicado al procesamiento de manuales PDF para el pipeline RAG.

---

## Stack técnico

| Tecnología | Uso |
|---|---|
| Python 3.12+ | Runtime |
| Redis | Coordinación de tareas con el backend |
| pydantic-settings | Configuración por variables de entorno |

---

## Estado actual

El worker funciona como una base funcional placeholder que mantiene el lugar arquitectónico correcto en el stack. El loop de ejecución y la infraestructura de logging están implementados; el pipeline de ingestión real está pendiente.

## Responsabilidades objetivo

| Etapa | Descripción |
|---|---|
| **Parsing** | Extracción de texto y estructura desde PDFs |
| **Chunking** | Segmentación del contenido en unidades recuperables |
| **Clasificación** | Detección de aplicabilidad por robot, ejes y versión |
| **Embeddings** | Generación de vectores para búsqueda semántica |
| **Indexación** | Carga de chunks y vectores en PostgreSQL + pgvector |

---

## Pruebas

```bash
docker compose exec worker python -m pytest
```
