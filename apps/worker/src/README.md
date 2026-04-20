# Estructura interna del worker

Organización del código fuente del pipeline de ingestión documental.

---

## Directorio `jobs/`

Definición de trabajos ejecutables. En la iteración actual contiene el loop operativo que reclama manuales pendientes, descarga el PDF, extrae texto, genera chunks y persiste el resultado.

## Directorio `core/`

Configuración del worker a partir de variables de entorno compartidas con el stack Docker.

## Directorio `db/`

Sesión SQLAlchemy y modelos persistentes necesarios para reclamar manuales y guardar chunks indexables.

## Directorio `parsers/`

Extracción de texto desde PDFs y detección de estructura documental (capítulos, secciones, tablas, ejemplos de código).

## Directorio `chunking/`

Segmentación del contenido extraído en unidades útiles para retrieval. La implementación actual genera chunks textuales base por página y tamaño máximo.

## Directorio `services/`

Integraciones externas del worker, como la descarga de manuales desde MinIO.

## Directorio `utils/`

Utilidades transversales del pipeline: logging estructurado y helpers compartidos.
