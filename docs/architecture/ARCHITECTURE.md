# Arquitectura — RC7 Programming Assistant

> Estos diagramas describen el sistema **como está en el código** (no una versión idealizada).
> Las divergencias con docs anteriores están registradas en
> [docs/audit/DOC_VS_CODE.md](../audit/DOC_VS_CODE.md).

## 1. Componentes y flujos de datos

```mermaid
flowchart TB
    Browser(["🌐 Browser"])

    subgraph Dev["🐳 docker-compose.yml (desarrollo)"]
        subgraph WEB["apps/web · Next.js 16 · :3000"]
            Next["App Router (SSR/CSR)"]
            Proxy["/api/v1/[...path] route handler\n(reenvía cookie, passthrough SSE)"]
        end
        API["apps/api · FastAPI · :8000\nauth · profile · chat · manuals\nadmin · settings · audit"]
        Worker["apps/worker · Python 3.12\npolling + FOR UPDATE SKIP LOCKED"]
        PG[("PostgreSQL 17 + pgvector\n:5432")]
        MinIO[("MinIO · :9000/:9001\nPDFs originales")]
    end

    Gemini(["☁️ Google Gemini API\ngemini-3.5-flash · gemini-embedding-2"])
    Nginx["Nginx :80/:443\n(SOLO docker-compose.prod.yml)"]

    Browser -->|"http :3000"| Next
    Browser -. "prod: https" .-> Nginx
    Nginx -. prod .-> Next
    Next --> Proxy
    Proxy -->|"http://api:8000"| API
    API -->|SQLAlchemy| PG
    API -->|upload/download/delete| MinIO
    API -->|"HyDE + embed + generación (SDK)"| Gemini
    Worker -->|"claim/insert chunks"| PG
    Worker -->|download PDF| MinIO
    Worker -->|"review (REST) + embed (SDK)"| Gemini
```

**Servicios realmente usados:** `web`, `api`, `worker`, `postgres` (imagen `pgvector/pgvector:pg17`),
`minio`. **Nginx existe solo en producción** (`docker-compose.prod.yml`) como terminador TLS/reverse
proxy; en desarrollo no hay nginx y el proxy de Next.js cumple ese rol para `/api/v1/*`.

---

## 2. Pipeline de ingestión (worker)

Implementación real en [jobs/ingestion.py](../../apps/worker/src/jobs/ingestion.py).

```mermaid
flowchart TD
    A["Admin: POST /api/v1/manuals (PDF)"] --> B["MinIO upload + INSERT manual (status=pending)"]
    B --> C["Worker loop (polling cada ~5s)\nclaim_next_pending_manual()\nSELECT FOR UPDATE SKIP LOCKED → processing"]
    C --> D["storage.download_manual() desde MinIO"]
    D --> E["extract_pdf_text_by_page() (pypdf, por página)"]
    E --> F{"¿texto útil?"}
    F -- No --> Z1["status=failed\nlast_error='No se pudo extraer texto util...'"]
    F -- Sí --> G["build_text_chunks() (semántico, max 1200 chars/párrafo)"]
    G --> H{"¿manual elegible?\n(idioma ∈ es,en y filtro de título)"}
    H -- No --> K["sin revisiones"]
    H -- Sí --> I["select_chunks_for_semantic_review()\nsample_rate=1.0 ⇒ TODOS\n(too_short / too_long / suspicious_boundary / sampled)"]
    I --> J["GeminiSemanticReviewer.review_chunk()\n1 llamada REST por chunk\ncoherence/completeness/boundary + action"]
    J --> L["apply_safe_chunk_autofixes()\nmerge_with_next / split (regenerate ⇒ keep)"]
    K --> L
    L --> M["embed_texts() gemini-embedding-2\n(1 types.Content por chunk, 3072 dims, batch=100)"]
    M --> N["index_manual_chunks(): DELETE previos +\nINSERT manual_chunks (embedding vector(3072))\n+ reviews + review_summary"]
    N --> O["status=indexed, chunk_count, indexed_at"]
    C -. "timeout dinámico excedido" .-> Z2["status=failed (timeout)"]
    C -. "crash / reinicio" .-> R["recover_stuck_processing_manuals()\nmarca '[crash]'; tras 3 ⇒ failed"]
```

Notas reales: la revisión es **exhaustiva** por defecto (`SEMANTIC_REVIEW_SAMPLE_RATE=1.0`, sin tope);
el autofix `regenerate` **no** está implementado (se trata como `keep`); el reviewer usa **REST urllib**
mientras el embedding usa el **SDK** ([CODE_AUDIT S5](../audit/CODE_AUDIT.md)).

---

## 3. Pipeline de consulta RAG (4 fases)

Implementación real en [chat/service.py](../../apps/api/src/services/chat/service.py).

```mermaid
flowchart TD
    Q["POST /api/v1/chat/generate (ChatRequest)"] --> P1["Fase 1 — HyDE\n_call_gemini() prosa, sin contexto\n(system=_PHASE1_SYSTEM)"]
    P1 --> P2["Fase 2 — Embed + Retrieve\n_embed_query('task: search result | query: '+prompt+HyDE[:600])\n_retrieve_chunks()"]
    P2 --> R1["pgvector: ORDER BY embedding::halfvec(3072) &lt;=&gt; query\nLIMIT 50 (HNSW)"]
    R1 --> R2["re-rank Python:\nscore = (1-distancia) · hardware_factor · category_factor\ntop_k (default 6)"]
    R2 --> P3["Fase 3 — Contexto\nfragmentos etiquetados [S1],[S2]… hasta budget chars\nsource_map: SID → (manual, página)"]
    P3 --> P4["Fase 4 — Generación final\n_call_gemini(force_json=True)\nsystem=_build_system_prompt (reglas PAC + trazabilidad)"]
    P4 --> PARSE["_parse_gemini_json() + _resolve_references()\n(descarta IDs alucinados; fallback al set recuperado)"]
    PARSE --> OUT["JSON: summary · pac_code (con ' fuente: SX) · references"]
    OUT --> SSE{"ENABLE_STREAMING?"}
    SSE -- "true" --> S1["SSE: chunk* → done\n(persistir historial + audit CHAT_QUERY)"]
    SSE -- "false" --> S2["único evento done (sync; 503 si falla)"]
```

Parámetros configurables en caliente (`system_settings`): `rag_top_k_chunks` (6),
`rag_context_budget_chars` (12000), `gemini_temperature` (0.7), `gemini_max_tokens` (8192),
`system_prompt_pac`, `history_max_entries` (50). El candidato pool (50) y los modelos están
hardcoded ([CODE_AUDIT S1, D1](../audit/CODE_AUDIT.md)).

---

## 4. Almacenamiento y recuperación vectorial

```mermaid
flowchart LR
    subgraph Write["Escritura (worker)"]
        W1["embed_texts()\ngemini-embedding-2, 3072 dims"] --> W2["manual_chunks.embedding\ncolumna vector(3072)"]
    end
    subgraph Schema["Esquema (init.py)"]
        X1["CREATE EXTENSION vector"] --> X2["columna vector(3072)\n(DROP+ADD idempotente)"]
        X2 --> X3["índice HNSW sobre\n(embedding::halfvec(3072)) halfvec_cosine_ops"]
    end
    subgraph Read["Lectura (API)"]
        R1["_embed_query(prefijo + query)"] --> R2["ORDER BY embedding::halfvec(3072) &lt;=&gt; q::halfvec(3072)\nLIMIT 50"]
        R2 --> R3["re-rank: similitud · hardware · categoría → top_k"]
    end
    W2 --- X2
    X3 -. acelera .-> R2
```

`halfvec`: pgvector limita los índices HNSW de `vector` a 2000 dims; para 3072 se indexa y consulta
vía cast a `halfvec(3072)`. La similitud = `1 − distancia_coseno (<=>)`.

---

## 5. Autenticación y auditoría

```mermaid
flowchart TD
    L["POST /auth/login (email+password)"] --> V{"verify_password (Argon2/pwdlib)\n& is_active"}
    V -- No --> F["401 + audit AUTH_FAILED"]
    V -- Sí --> T["JWT HS256 firmado (sub,email,role,available_roles)\nSet-Cookie rc7_session (HttpOnly, SameSite=lax)"]
    T --> AUD["audit AUTH_LOGIN"]
    REQ["Request protegido"] --> GC["get_current_user(): lee cookie → decode JWT → carga User"]
    GC -->|inválido/inactivo| E401["401"]
    GC -->|admin route| GA["get_current_admin_user(): rol activo == admin?"]
    GA -->|no| E403["403"]
    subgraph Audit["audit_service.log_event() — best-effort"]
        AE["INSERT audit_log\n(captura toda excepción → logger; nunca relanza)"]
    end
    AUD --> AE
    F --> AE
```

**Estado real:** Google SSO **no implementado** (`/auth/providers` solo informa). Hashing con
**Argon2** (`pwdlib.recommended()`), no bcrypt. El audit nunca rompe el flujo principal. Observabilidad =
audit_log + logs rotados a archivo (`api.log` / `worker.log`).

---

## 6. Diagrama de secuencia — Vida de una consulta

```mermaid
sequenceDiagram
    actor U as Usuario
    participant W as Next.js (web)
    participant PX as Proxy /api/v1
    participant A as FastAPI (chat)
    participant DB as PostgreSQL+pgvector
    participant G as Gemini

    U->>W: prompt + config robot
    W->>PX: POST /api/v1/chat/generate (cookie)
    PX->>A: POST (Connection: close, cookie)
    A->>A: get_current_user (401 si falla)
    A->>G: Fase 1 HyDE (prosa)
    G-->>A: respuesta hipotética
    A->>G: Fase 2 embed(query + HyDE)
    G-->>A: vector 3072
    A->>DB: ORDER BY embedding &lt;=&gt; q LIMIT 50
    DB-->>A: candidatos
    A->>A: re-rank hardware+categoría → top_k, source_map
    A->>G: Fase 4 generación (force_json, stream)
    loop tokens
        G-->>A: chunk
        A-->>PX: data: {type:chunk}
        PX-->>W: SSE passthrough
        W-->>U: render incremental
    end
    A-->>PX: data: {type:done, summary, pac_code, references}
    A->>DB: guarda chat_history (poda) + audit CHAT_QUERY
    PX-->>W: done
```

---

## 7. Diagrama de secuencia — Vida de un manual (ingestión)

```mermaid
sequenceDiagram
    actor Adm as Admin
    participant A as FastAPI (manuals)
    participant S as MinIO
    participant DB as PostgreSQL
    participant Wk as Worker
    participant G as Gemini

    Adm->>A: POST /api/v1/manuals (PDF, multipart)
    A->>A: valida PDF + SHA-256 (409 si duplicado)
    A->>S: upload_manual()
    A->>DB: INSERT manual (status=pending) + audit MANUAL_UPLOADED
    loop polling ~5s
        Wk->>DB: claim_next_pending_manual (FOR UPDATE SKIP LOCKED)
    end
    Wk->>DB: status=processing
    Wk->>S: download_manual()
    Wk->>Wk: extract_pdf_text_by_page → build_text_chunks
    alt manual elegible
        loop por chunk (todos)
            Wk->>G: review_chunk (REST)
            G-->>Wk: scores + action
        end
        Wk->>Wk: apply_safe_chunk_autofixes
    end
    Wk->>G: embed_texts (batch, 3072)
    G-->>Wk: embeddings
    Wk->>DB: INSERT chunks(vector) + reviews + summary
    Wk->>DB: status=indexed, indexed_at
```

---

## 8. Modelo de datos (ER)

Relaciones con **FK declarada** = líneas sólidas. Referencias lógicas (columna `int` indexada sin
`ForeignKey`: `chat_history.user_id`, `audit_log.actor_id`, `system_settings.updated_by`,
`manuals.uploaded_by_user_id`) se documentan en nota, no como relación.

```mermaid
erDiagram
    USERS ||--o{ MANUALS : "uploaded_by (lógico)"
    MANUALS ||--o{ MANUAL_CHUNKS : "FK manual_id"
    MANUALS ||--o{ MANUAL_CHUNK_REVIEWS : "FK manual_id"
    MANUALS ||--|| MANUAL_REVIEW_SUMMARIES : "FK manual_id (unique)"
    USERS ||--o{ CHAT_HISTORY : "user_id (lógico)"

    USERS {
        int id PK
        string email UK
        string display_name
        string password_hash
        json roles
        json profile_settings
        bool is_active
        datetime created_at
        datetime updated_at
    }
    MANUALS {
        int id PK
        string title
        string original_filename
        string storage_key UK
        string content_type
        int size_bytes
        string sha256
        string status
        int chunk_count
        string robot_model
        string controller_version
        string document_language
        array categories
        text notes
        text last_error
        int uploaded_by_user_id
        string uploaded_by_email
        datetime processing_started_at
        datetime indexed_at
        datetime created_at
        datetime updated_at
    }
    MANUAL_CHUNKS {
        int id PK
        int manual_id FK
        int chunk_index
        int page_number
        text text
        vector embedding "vector(3072)"
        datetime created_at
    }
    MANUAL_CHUNK_REVIEWS {
        int id PK
        int manual_id FK
        int chunk_index
        int page_number
        string review_status
        string selected_reason
        string action
        string reviewer_model
        float coherence_score
        float completeness_score
        float boundary_quality_score
        text reason
        text raw_response
        datetime created_at
    }
    MANUAL_REVIEW_SUMMARIES {
        int id PK
        int manual_id FK "unique"
        int initial_chunk_count
        int final_chunk_count
        int reviewed_count
        int skipped_count
        int error_count
        int merge_actions
        int split_actions
        int keep_actions
        int regenerate_actions
        int applied_autofixes
        float avg_coherence_score
        float avg_completeness_score
        float avg_boundary_quality_score
        int estimated_input_tokens
        int estimated_output_tokens
        float estimated_cost_usd
        datetime created_at
        datetime updated_at
    }
    CHAT_HISTORY {
        int id PK
        int user_id "indexado (lógico)"
        text prompt
        text summary
        text pac_code
        json references
        json robot_config
        string entry_type
        datetime created_at
    }
    ROLE_PERMISSIONS {
        int id PK
        string key UK
        string name
        string description
        bool admin
        bool user
        datetime created_at
        datetime updated_at
    }
    SYSTEM_SETTINGS {
        int id PK
        string key UK
        text value
        string description
        datetime updated_at
        int updated_by "lógico"
    }
    AUDIT_LOG {
        string id PK "uuid"
        string event_type
        int actor_id "lógico"
        string actor_email
        string resource_type
        string resource_id
        text description
        json event_metadata
        string ip_address
        datetime created_at
    }
```

`ROLE_PERMISSIONS`, `SYSTEM_SETTINGS` y `AUDIT_LOG` son tablas independientes (sin FK). El modelo
`Manual` del worker es un subconjunto del de la API (no declara `sha256`) — ver
[CODE_AUDIT O2](../audit/CODE_AUDIT.md).
