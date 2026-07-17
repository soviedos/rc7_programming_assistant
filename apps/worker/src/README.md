# Estructura interna del worker

Organización del código fuente del pipeline de ingestión documental.

---

## Directorio `jobs/`

Definición de trabajos ejecutables. Contiene el loop operativo (`ingestion.py`), que reclama
manuales pendientes con `FOR UPDATE SKIP LOCKED`, calcula un timeout proporcional al tamaño,
descarga el PDF, extrae texto, genera chunks, los somete a revisión semántica con Gemini,
aplica autocorrecciones seguras (merge/split/regenerate), genera los embeddings y persiste
chunks y revisiones. También recupera manuales que quedaron atascados en `processing`.

## Directorio `core/`

Configuración del worker a partir de variables de entorno compartidas con el stack Docker.

## Directorio `db/`

Sesión SQLAlchemy y modelos persistentes necesarios para reclamar manuales y guardar chunks indexables.

## Directorio `parsers/`

Extracción de texto página a página con pypdf (`extract_pdf_text_by_page`) y lectura del
outline del PDF para anotar cada página con su sección (`extract_page_sections`). No detecta
tablas ni ejemplos de código.

## Directorio `chunking/`

Segmentación del contenido extraído en unidades útiles para retrieval. Es **estructural**, no
semántica: empaqueta párrafos por página hasta 1200 chars y, si un párrafo se pasa, lo parte
por índice. La evaluación semántica es la etapa siguiente (`services/semantic_review.py`).

## Directorio `services/`

Integraciones externas: MinIO para descargar los PDFs (`storage.py`) y Gemini tanto para los
embeddings (`embeddings.py`) como para la revisión semántica y la regeneración de chunks
(`semantic_review.py`).

## Directorio `utils/`

Utilidades transversales del pipeline: logging estructurado y helpers compartidos.
