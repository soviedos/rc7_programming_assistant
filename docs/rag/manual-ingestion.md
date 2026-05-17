# Ingestión de Manuales

## Objetivo

Transformar manuales PDF oficiales de DENSO en una base de conocimiento vectorial recuperable por semántica.

---

## Supuestos

| Supuesto | Detalle |
|---|---|
| Calidad de los PDFs | Los manuales tienen buena calidad digital; el texto es extraíble sin depender de OCR |
| Estructura documental | Los documentos siguen una estructura de capítulos y secciones identificable |

---

## Pipeline de ingestión

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Upload    │───▶│   Parsing   │───▶│  Chunking   │───▶│  Revisión   │───▶│ Embeddings  │
│  (MinIO)    │    │  (pypdf)    │    │ (semántico) │    │  semántica  │    │  (Gemini)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                                    │
                                                                             ┌──────▼──────┐
                                                                             │ Indexación  │
                                                                             │ (pgvector)  │
                                                                             └─────────────┘
```

### 1. Subida del PDF

El archivo se sube a MinIO y se registra en la base de datos con estado `pending`.

### 2. Parsing

El worker detecta el manual pendiente mediante polling a PostgreSQL, descarga el PDF desde MinIO y extrae el texto página a página con `pypdf`.

### 3. Chunking semántico

El texto extraído se divide en fragmentos de tamaño controlado, respetando párrafos y estructura del documento.

### 4. Revisión semántica

Cada chunk pasa por Gemini para verificar coherencia y corregir artefactos de extracción (saltos de línea espurios, encabezados fragmentados, etc.). Los chunks con contenido insuficiente se descartan.

### 5. Generación de embeddings

Los chunks revisados se vectorizan en lotes con `gemini-embedding-001` (768 dimensiones, task type `RETRIEVAL_DOCUMENT`).

### 6. Indexación

Chunks y vectores se persisten en PostgreSQL + pgvector. El estado del manual se actualiza a `ready` al terminar o `failed` si hay errores irrecuperables.

---

## Estructura de un chunk indexado

| Campo | Descripción |
|---|---|
| `text` | Contenido textual del fragmento |
| `page` | Número de página en el PDF original |
| `chunk_index` | Posición del chunk dentro del manual |
| `embedding` | Vector de 768 dimensiones (ARRAY REAL, nullable mientras se genera) |
| `manual_id` | Referencia al manual de origen |

| `source_file` | Referencia al archivo PDF original en MinIO |
| `embedding` | Vector generado para búsqueda semántica |

---

## Justificación

No basta con recuperar texto semánticamente similar. El sistema debe filtrar el contexto por la configuración técnica del robot del usuario para evitar respuestas que apliquen a un modelo diferente o una versión incompatible del controlador.
