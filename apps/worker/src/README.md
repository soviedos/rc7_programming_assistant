# Estructura interna del worker

## `jobs/`

Definicion de trabajos ejecutables.

## `parsers/`

Extraccion de texto desde PDFs y deteccion de estructura documental.

## `chunking/`

Segmentacion del contenido en unidades utiles para retrieval.

## `classifiers/`

Deteccion de aplicabilidad tecnica:

- tipo de robot
- numero de ejes
- soporte de vision
- versiones del controlador

## `embeddings/`

Generacion y normalizacion de embeddings.

## `indexing/`

Carga de chunks y vectores en PostgreSQL + pgvector.

## `utils/`

Utilidades transversales del pipeline.
