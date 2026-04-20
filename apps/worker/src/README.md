# Estructura interna del worker

Organización del código fuente del pipeline de ingestión documental.

---

## Directorio `jobs/`

Definición de trabajos ejecutables. Cada job encapsula una unidad de trabajo completa que puede ser disparada desde el backend vía Redis.

## Directorio `parsers/`

Extracción de texto desde PDFs y detección de estructura documental (capítulos, secciones, tablas, ejemplos de código).

## Directorio `chunking/`

Segmentación del contenido extraído en unidades útiles para retrieval. Los chunks se dimensionan para maximizar la relevancia en búsqueda semántica.

## Directorio `classifiers/`

Detección de aplicabilidad técnica de cada chunk:

| Dimensión | Descripción |
|---|---|
| Tipo de robot | 4-axis, 6-axis |
| Soporte de visión | Habilitado / No habilitado |
| Versión del controlador | Versión mínima requerida |
| Aplicabilidad | Todos los robots o modelos específicos |

## Directorio `embeddings/`

Generación y normalización de embeddings vectoriales para cada chunk procesado.

## Directorio `indexing/`

Carga de chunks y vectores en PostgreSQL + pgvector, con metadatos de clasificación y referencia al documento original.

## Directorio `utils/`

Utilidades transversales del pipeline: logging, manejo de archivos temporales y helpers compartidos.
