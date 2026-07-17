# Worker — Pipeline de ingestión documental

Proceso asincrónico del RC7 Programming Assistant, dedicado al procesamiento de manuales PDF para el pipeline RAG.

---

## Stack técnico

| Tecnología | Uso |
|---|---|
| Python 3.12+ | Runtime |
| SQLAlchemy + psycopg | Acceso a PostgreSQL |
| pgvector | Tipo de columna `Vector(3072)` para embeddings |
| google-genai SDK | Revisión semántica y embeddings (`gemini-embedding-2`) |
| MinIO SDK | Descarga de manuales PDF |
| pypdf | Extracción de texto por página |
| pydantic-settings | Configuración por variables de entorno |

---

## Pipeline (implementado)

El worker ejecuta el pipeline completo de ingestión:

- Detecta manuales con estado `pending` (`FOR UPDATE SKIP LOCKED`)
- Los marca como `processing`
- Descarga el PDF desde MinIO
- Extrae texto por página con pypdf
- Genera chunks estructurales por página y presupuesto de caracteres
  (`build_text_chunks`, 1200 chars; lo semántico es la etapa siguiente)
- Revisión semántica con Gemini de **todos los chunks** (sin muestreo por defecto):
  `coherence`, `completeness`, `boundary` + autocorrecciones seguras (merge/split/regenerate)
- Genera embeddings por chunk con `gemini-embedding-2` (3072-dim, un `types.Content` por chunk)
- Persiste los chunks en PostgreSQL (`manual_chunks.embedding vector(3072)`)
- Marca el manual como `indexed` o `failed`

## Etapas

| Etapa | Descripción |
|---|---|
| **Parsing** | Extracción de texto por página desde PDFs con pypdf |
| **Chunking** | Segmentación estructural: empaqueta párrafos por página hasta 1200 chars, sin solapamiento y sin cruzar página |
| **Revisión** | Evaluación con Gemini de todos los chunks + autocorrección segura |
| **Embeddings** | Generación de vectores `gemini-embedding-2` (3072-dim) por chunk |
| **Indexación** | Carga de chunks y vectores en PostgreSQL + pgvector (`vector(3072)`). El índice HNSW lo crea la API al inicializar la BD, no el worker |

### Cobertura de revisión (variables de entorno)

Los defaults viven en [`src/core/config.py`](src/core/config.py) y aplican **sin** `.env`:
`semantic_review_sample_rate=1.0` (todos los chunks), `semantic_review_max_reviews_per_manual=0`
(sin tope) y timeouts elevados (`worker_manual_timeout_seconds=7200`,
`worker_manual_timeout_max_seconds=21600`) para no fallar al revisar manuales grandes.

En `.env.example` esas variables están **comentadas**: solo documentan cómo sobrescribir los
defaults, no los fijan.

### Re-embedding del corpus

Tras cambiar el modelo de embeddings, los espacios son incompatibles: hay que invalidar y
re-embeber todo el corpus.

```bash
docker compose exec postgres psql -U postgres -d rc7_assistant -c "UPDATE manual_chunks SET embedding = NULL;"
docker compose exec worker python -m scripts.reembed_chunks
```

---

## Pruebas

```bash
docker compose exec worker python -m pytest
```
