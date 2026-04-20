# Ingestión de Manuales

## Objetivo

Transformar manuales PDF oficiales de DENSO en una base de conocimiento confiable, recuperable y filtrable por contexto técnico.

---

## Supuestos

| Supuesto | Detalle |
|---|---|
| Calidad de los PDFs | Los manuales tienen buena calidad digital; el texto es extraíble sin depender de OCR |
| Estructura documental | Los documentos siguen una estructura de capítulos, secciones y ejemplos identificable |
| Aplicabilidad variable | Cada tema puede aplicar a diferentes tipos de robot o versiones del controlador |

---

## Pipeline de ingestión

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Upload    │───▶│   Parsing   │───▶│  Chunking   │───▶│ Classifica- │
│  (MinIO)    │    │  (texto +   │    │ (segmenta-  │    │   ción      │
│             │    │  estructura)│    │   ción)     │    │ (aplicab.)  │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                │
                                                         ┌──────▼──────┐    ┌─────────────┐
                                                         │ Embeddings  │───▶│ Indexación   │
                                                         │ (vectores)  │    │ (pgvector)   │
                                                         └─────────────┘    └─────────────┘
```

### 1. Subida del PDF

El archivo se almacena en MinIO y se registra en la base de datos con sus metadatos.

### 2. Parsing

Extracción de texto y detección de estructura documental (capítulos, secciones, tablas).

### 3. Segmentación (chunking)

División del contenido en unidades recuperables, organizadas por:

- Capítulo y sección
- Comandos PAC
- Ejemplos de código
- Tablas de referencia

### 4. Clasificación de aplicabilidad

Cada chunk se clasifica por su contexto técnico:

| Dimensión | Valores posibles |
|---|---|
| Tipo de robot | 4-axis, 6-axis |
| Soporte de visión | Sí, No |
| Aplicabilidad | Todos los robots, modelos específicos |
| Versión mínima | Versión del controlador RC7 requerida |

### 5. Generación de embeddings

Vectorización del contenido textual de cada chunk para búsqueda semántica.

### 6. Indexación

Carga de chunks y vectores en PostgreSQL + pgvector, con metadatos de clasificación asociados.

---

## Estructura de un chunk indexado

| Campo | Descripción |
|---|---|
| `text` | Contenido textual del fragmento |
| `page` | Número de página en el PDF original |
| `section` | Sección del manual |
| `commands` | Comandos PAC detectados en el fragmento |
| `applicability` | Clasificación técnica (robot, ejes, visión, versión) |
| `source_file` | Referencia al archivo PDF original en MinIO |
| `embedding` | Vector generado para búsqueda semántica |

---

## Justificación

No basta con recuperar texto semánticamente similar. El sistema debe filtrar el contexto por la configuración técnica del robot del usuario para evitar respuestas que apliquen a un modelo diferente o una versión incompatible del controlador.
