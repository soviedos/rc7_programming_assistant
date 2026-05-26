# Ingestión de Manuales — Pipeline Documental

El pipeline de ingestión convierte PDFs de manuales DENSO RC7 en chunks de texto embebidos
y almacenados en pgvector, listos para el retrieval del chat RAG.

---

## Flujo completo

```text
Admin → POST /api/v1/manuals/
    │
    ├─ MinIO: upload PDF (bucket rc7-manuals)
    └─ PostgreSQL: INSERT manual (status=pending)
             │
             ▼
    Worker (polling SQL cada ~5 s)
    claim_next_pending_manual()
    SELECT ... FOR UPDATE SKIP LOCKED → status=processing
             │
             ▼
    [Etapa 1] Extracción de texto
    pypdf → extract_pdf_text_by_page()
    ├─ Descarga PDF desde MinIO
    └─ Texto extraído por página con pypdf, preservando números de página
             │
             ▼
    [Etapa 2] Chunking semántico
    build_text_chunks()
    ├─ Segmentación respetando párrafos naturales
    ├─ Tamaño target y solapamiento configurables en código
    └─ Cada chunk lleva: texto, página de inicio, página de fin
             │
             ▼
    [Etapa 3] Revisión semántica con Gemini
    GeminiSemanticReviewer (muestra configurable del total de chunks)
    ├─ Evalúa: coherence_score, completeness_score, boundary_quality_score
    ├─ Acción por chunk: keep | merge | split | regenerate
    └─ apply_safe_chunk_autofixes(): aplica correcciones automáticas seguras
    Resultados guardados en: manual_chunk_reviews, manual_review_summaries
             │
             ▼
    [Etapa 4] Embedding
    embed_texts()
    ├─ Modelo: gemini-embedding-001 (768 dimensiones)
    ├─ task_type: RETRIEVAL_DOCUMENT
    ├─ Procesado en lote (batch)
    └─ Timeout por lote configurable
             │
             ▼
    INSERT manual_chunks (texto + embedding REAL[] + página)
    UPDATE manual (status=indexed)  ←── estado final exitoso
             │
             ▼
    Chunks disponibles para retrieval en próximas consultas de chat
```

**En caso de error:** `status=failed`, se guarda el mensaje de error en la tabla del manual.
La ingestión puede reintentarse desde la consola de administración con `POST /api/v1/manuals/{id}/retry`.

**Cancelación:** Un manual en `pending` o `processing` puede cancelarse con
`POST /api/v1/manuals/{id}/cancel`. Elimina los chunks parciales y marca el manual como `failed`
con el mensaje "Cancelado por el usuario.". Disponible desde el botón "Detener" en la consola admin.

---

## Estados del manual

| Estado | Significado |
|---|---|
| `pending` | Subido pero aún no procesado por el worker |
| `processing` | Worker actualmente procesando el manual |
| `indexed` | Ingestión completada; chunks disponibles para RAG |
| `failed` | Ingestión fallida o cancelada; el campo `error_message` contiene el detalle |

**Resiliencia ante crashes:** Si el worker muere mientras procesa un manual (p.ej. por OOM),
el registro queda en `processing`. Al reiniciar, el worker re-encola automáticamente los manuales
atascados, marcando un contador de crashes en `last_error`. Tras 3 crashes consecutivos el manual
se marca como `failed` para evitar bucles infinitos.
Un manual atascado manualmente puede liberarse con
`POST /api/v1/manuals/cleanup-stale-processing` (admin).

---

## Parámetros configurables

Los siguientes parámetros afectan al retrieval en el pipeline RAG y son ajustables en caliente
desde la consola de administración (sin reiniciar el stack):

| Parámetro (clave en settings) | Default | Efecto |
|---|---|---|
| `rag_top_k_chunks` | `6` | Número de chunks recuperados por consulta en la búsqueda coseno |
| `rag_context_budget_chars` | `12000` | Presupuesto total de caracteres de contexto enviado a Gemini en Fase 4 |

Ver [docs/backend/settings-module.md](../backend/settings-module.md) para la tabla completa.

---

## Revisión semántica — detalles

La revisión semántica (`GeminiSemanticReviewer`) evalúa una muestra de los chunks generados
con Gemini para detectar problemas de calidad en la segmentación:

| Métrica | Descripción |
|---|---|
| `coherence_score` | El chunk tiene sentido completo por sí solo (0.0–1.0) |
| `completeness_score` | El chunk no está cortado a mitad de una idea (0.0–1.0) |
| `boundary_quality_score` | Los bordes del chunk coinciden con límites naturales (0.0–1.0) |

**Acciones de autocorrección seguras** (`apply_safe_chunk_autofixes`):
- `keep` — chunk aceptado sin modificación
- `merge` — chunk muy corto fusionado con el siguiente
- `split` — chunk muy largo dividido en mitades iguales
- `regenerate` — chunk regenerado con prompt de reformulación (no implementado aún; tratado como `keep`)

Los resultados agregados por manual se almacenan en `manual_review_summaries` y son
consultables desde la consola de administración en `/api/v1/manuals/review-summaries`.

---

## Retrieval — pipeline RAG (Fase 2)

Durante el chat, la búsqueda de chunks utiliza:

1. **Embedding de la consulta + respuesta hipotética HyDE** (768 dims, task_type=RETRIEVAL_QUERY)
2. **Búsqueda coseno** sobre `manual_chunks` (solo manuales con `status=indexed`)
3. **Boost por categoría:** los manuales de programación (`programming`) reciben un multiplicador
   de similitud adicional (×1.30) para priorizar contenido relevante
4. **Top-k** seleccionado según `rag_top_k_chunks` (configurable)
5. **Budget:** chunks incluidos hasta agotar `rag_context_budget_chars` (configurable)

---

## Comandos de administración

| Endpoint | Descripción |
|---|---|
| `POST /api/v1/manuals/` | Subir nuevo PDF y disparar ingestión |
| `POST /api/v1/manuals/{id}/retry` | Reintentar ingestión en manual `failed` |
| `POST /api/v1/manuals/cleanup-stale-processing` | Liberar manuales atascados en `processing` |
| `GET /api/v1/manuals/review-summaries` | Ver métricas de revisión semántica por manual |
| `DELETE /api/v1/manuals/{id}` | Eliminar manual, chunks, embeddings y PDF de MinIO |
