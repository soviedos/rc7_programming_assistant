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
    [Etapa 2] Chunking estructural  (NO semántico — lo semántico es la etapa 3)
    build_text_chunks()
    ├─ Página por página: un chunk NUNCA cruza de página
    ├─ Empaqueta párrafos (\n\n) hasta 1200 chars — fijo en código, sin ajuste
    ├─ Un párrafo > 1200 chars se corta a ciegas cada 1200 (puede partir palabras)
    ├─ SIN solapamiento: los chunks son disjuntos
    └─ Cada chunk lleva: texto y su número de página (uno solo)
             │
             ▼
    [Etapa 3] Revisión semántica con Gemini
    GeminiSemanticReviewer (TODOS los chunks — sin muestreo por defecto)
    ├─ Evalúa: coherence_score, completeness_score, boundary_quality_score
    ├─ Acción por chunk: keep | merge | split | regenerate
    └─ apply_safe_chunk_autofixes(): aplica correcciones automáticas seguras
    Resultados guardados en: manual_chunk_reviews, manual_review_summaries
             │
             ▼
    [Etapa 4] Embedding
    embed_texts()
    ├─ Modelo: gemini-embedding-2 (3072 dimensiones)
    ├─ Sin task_type: cada chunk se envuelve en su propio types.Content
    │   con prefijo "title: none | text: …" (un embedding por chunk)
    ├─ Procesado en lote (batch)
    └─ Timeout por lote configurable
             │
             ▼
    INSERT manual_chunks (texto + embedding vector(3072) + página)
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
| `failed` | Ingestión fallida o cancelada; el campo `last_error` contiene el detalle |

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

> **Dónde vive lo semántico.** El corte inicial (etapa 2) es mecánico: párrafos y un
> presupuesto de 1200 chars, sin entender el texto. La comprensión entra **aquí**, en
> la etapa 3: Gemini revisa los chunks ya cortados y repara los cortes malos. La
> arquitectura es *cortar mecánicamente y reparar semánticamente*, no cortar con
> criterio semántico desde el principio. Ejemplo real: un manual entró con 318 chunks
> y salió con 230 tras 104 autofixes.

La revisión semántica (`GeminiSemanticReviewer`) evalúa **todos los chunks generados**
(con la configuración por defecto, sin muestreo) con Gemini para detectar problemas de
calidad en la segmentación:

| Métrica | Descripción |
|---|---|
| `coherence_score` | El chunk tiene sentido completo por sí solo (0.0–1.0) |
| `completeness_score` | El chunk no está cortado a mitad de una idea (0.0–1.0) |
| `boundary_quality_score` | Los bordes del chunk coinciden con límites naturales (0.0–1.0) |

**Acciones de autocorrección seguras** (`apply_safe_chunk_autofixes`,
[jobs/ingestion.py](../../apps/worker/src/jobs/ingestion.py)):
- `keep` — chunk aceptado sin modificación.
- `merge_with_next` — chunk fusionado con el siguiente (misma página) cuando
  `boundary_quality_score ≤ SEMANTIC_REVIEW_MERGE_BOUNDARY_MAX`.
- `split` — chunk largo dividido en dos cuando `len ≥ SEMANTIC_REVIEW_SPLIT_MIN_CHARS` y
  `coherence_score ≤ SEMANTIC_REVIEW_SPLIT_MAX_COHERENCE`.
- `regenerate` — **implementado**: si `coherence_score ≤ SEMANTIC_REVIEW_REGENERATE_MAX_COHERENCE`,
  el worker llama a Gemini (`GeminiSemanticReviewer.regenerate_chunk`,
  [semantic_review.py](../../apps/worker/src/services/semantic_review.py)) para **reescribir el
  texto del chunk** corrigiendo artefactos de extracción (saltos de línea espurios, encabezados
  o palabras fragmentadas) **sin inventar contenido ni alterar el significado**. El texto corregido
  se aplica **antes del embedding** (se embebe e indexa la versión reescrita) y la acción se registra
  en `manual_chunk_reviews`. Es fail-safe: si la reescritura falla o vuelve vacía/igual, se hace `keep`.

Cada `regenerate` es **una llamada Gemini adicional por chunk**, acotada doblemente: solo chunks ya
revisados (sujetos al tope de revisión) y con coherencia ≤ el umbral.

Los resultados agregados por manual se almacenan en `manual_review_summaries` (incluye
`regenerate_actions` y `applied_autofixes`) y son consultables en `/api/v1/manuals/review-summaries`.

### Cobertura de la revisión (variables de entorno del worker)

Por defecto el worker inspecciona **todos** los chunks de cada manual elegible, sin muestreo
ni tope. Los valores de abajo son los defaults del código
([config.py](../../apps/worker/src/core/config.py)), así que aplican aunque no exista `.env`;
sobrescribir solo si se quiere reducir cobertura:

| Variable | Valor por defecto | Efecto |
|---|---|---|
| `SEMANTIC_REVIEW_SAMPLE_RATE` | `1.0` | Fracción de chunks revisados. `1.0` = todos (sin muestreo) |
| `SEMANTIC_REVIEW_MAX_REVIEWS_PER_MANUAL` | `0` | Tope de revisiones por manual. `0` desactiva el tope |
| `SEMANTIC_REVIEW_AUTOFIX_ENABLED` | `true` | Activa merge/split/regenerate tras la revisión |
| `SEMANTIC_REVIEW_REGENERATE_MAX_COHERENCE` | `0.5` | Solo reescribe (regenerate) si la coherencia es ≤ este valor (control de costo) |
| `WORKER_MANUAL_TIMEOUT_SECONDS` | `7200` | Timeout base por manual; subido para que revisar todos los chunks no falle |
| `WORKER_MANUAL_TIMEOUT_MAX_SECONDS` | `21600` | Tope del timeout dinámico (escala con el tamaño del PDF) |

> Revisar todos los chunks implica **una llamada a Gemini por chunk**: mucho más lento y costoso
> que el muestreo. Sólo aplica a nuevas ingestiones o reintentos; los manuales ya indexados no se
> re-revisan hasta reprocesarlos. Para reducir costo, bajar `SEMANTIC_REVIEW_SAMPLE_RATE` o fijar
> un tope con `SEMANTIC_REVIEW_MAX_REVIEWS_PER_MANUAL`.

---

## Retrieval — pipeline RAG (Fase 2)

Durante el chat, la búsqueda de chunks utiliza:

1. **Embedding de la consulta + respuesta hipotética HyDE** (`gemini-embedding-2`, 3072 dims).
   `gemini-embedding-2` no admite `task_type`; en su lugar la query se prefija con
   `"task: search result | query: …"`.
2. **Búsqueda vectorial en pgvector** con el operador de distancia coseno `<=>` sobre
   `manual_chunks` (solo manuales con `status=indexed`). Acelerada por un índice **HNSW**
   construido sobre un cast a `halfvec(3072)` (pgvector limita los índices HNSW de `vector`
   a 2000 dims). Se recupera un pool amplio de candidatos (top-50) ordenado por distancia.
3. **Re-ranking en Python** del pool con la fórmula de scoring:

   ```text
   score(chunk) = cosine_similarity · hardware_factor · category_factor
   ```

   - `cosine_similarity = 1 − (embedding <=> query)`.
   - `hardware_factor = robot_factor · controller_factor` — prioriza chunks cuyo manual
     coincide con la configuración del robot del usuario (`ChatRequest`): modelo
     (`robot_model` vs `robot_type`) y controlador/firmware (`controller_version` vs
     `controller`). Match → boost (×1.30 / ×1.15); presente pero distinto → penalización
     suave (×0.70 / ×0.85); **sin metadato → neutral (×1.0), nunca degrada**.
   - `category_factor` — boost secundario por categoría documental (p. ej. `programming` ×1.30).
4. **Top-k** seleccionado según `rag_top_k_chunks` (configurable). Los chunks incompatibles se
   *demoten* en vez de filtrarse, así el contexto nunca queda vacío si ningún manual coincide
   exactamente con el hardware.
5. **Budget:** chunks incluidos hasta agotar `rag_context_budget_chars` (configurable).

### Trazabilidad de fuentes

En Fase 3 cada fragmento de contexto se etiqueta con un ID estable (`S1`, `S2`, …) y se
construye un `source_map` `ID → (manual, página)`. El system prompt exige que cada instrucción
o bloque PAC generado lleve un comentario de fuente (`' fuente: S2`, válido en PAC por el
apóstrofo).

El array `references` que devuelve el modelo se **ignora a propósito**:
`_resolve_references` solo recibe el `source_map` y emite una entrada por cada SID
que contenga, ordenadas S1…Sn. Así la leyenda cubre todos los `S<n>` que pueden
aparecer citados en el código, ningún ID queda sin resolver y no hace falta
descartar IDs alucinados: el `source_map` es la única fuente de verdad y se
persiste con el mensaje, de modo que un SID nunca se re-decodifica en un turno
posterior.

---

## Comandos de administración

| Endpoint | Descripción |
|---|---|
| `POST /api/v1/manuals/` | Subir nuevo PDF y disparar ingestión |
| `POST /api/v1/manuals/{id}/retry` | Reintentar ingestión en manual `failed` |
| `POST /api/v1/manuals/cleanup-stale-processing` | Liberar manuales atascados en `processing` |
| `GET /api/v1/manuals/review-summaries` | Ver métricas de revisión semántica por manual |
| `DELETE /api/v1/manuals/{id}` | Eliminar manual, chunks, embeddings y PDF de MinIO |
