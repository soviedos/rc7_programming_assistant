# Arquitectura — RC7 Programming Assistant

> Estos diagramas describen el sistema **como está en el código** (no una versión idealizada).
> Las divergencias con docs anteriores están registradas en
> [docs/audit/DOC_VS_CODE.md](../audit/DOC_VS_CODE.md).

## 1. Componentes y flujos de datos

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontFamily':'ui-sans-serif, system-ui','fontSize':'14px','lineColor':'#94a3b8'},'flowchart':{'curve':'basis','nodeSpacing':45,'rankSpacing':60}}}%%
flowchart TB
    Browser(["🌐 Browser"]):::client

    subgraph Dev["🐳 docker-compose.yml · desarrollo"]
        subgraph WEB["apps/web · Next.js 16 · :3000"]
            Next["App Router · SSR/CSR"]:::frontend
            Proxy["/api/v1/[...path] route handler\nreenvía cookie · passthrough SSE"]:::frontend
        end
        API["apps/api · FastAPI · :8000\nauth · profile · chat · manuals\nadmin · settings · audit"]:::backend
        Worker["apps/worker · Python 3.12\npolling + FOR UPDATE SKIP LOCKED"]:::worker
        PG[("PostgreSQL 17 + pgvector\n:5432")]:::data
        MinIO[("MinIO · :9000/:9001\nPDFs originales")]:::data
    end

    Gemini(["☁️ Google Gemini API\ngemini-3.5-flash · gemini-embedding-2"]):::external
    Nginx["Nginx :80/:443\nSOLO docker-compose.prod.yml"]:::prod

    Browser -->|"http :3000"| Next
    Browser -. "prod: https" .-> Nginx
    Nginx -. prod .-> Next
    Next --> Proxy
    Proxy -->|"http://api:8000"| API
    API -->|SQLAlchemy| PG
    API -->|upload/download/delete| MinIO
    API -->|"HyDE · embed · generación (SDK)"| Gemini
    PG -.->|"poll · claim manual pendiente\n(FOR UPDATE SKIP LOCKED)"| Worker
    Worker -->|"INSERT chunks + reviews"| PG
    Worker -->|download PDF| MinIO
    Worker -->|"review + embed (SDK)"| Gemini

    classDef client fill:#0f172a,stroke:#e2e8f0,stroke-width:2px,color:#f1f5f9
    classDef frontend fill:#0b3d5c,stroke:#38bdf8,stroke-width:2px,color:#e0f2fe
    classDef backend fill:#0f3d2e,stroke:#34d399,stroke-width:2px,color:#d1fae5
    classDef worker fill:#4a2f0a,stroke:#fbbf24,stroke-width:2px,color:#fef3c7
    classDef data fill:#2e1065,stroke:#a78bfa,stroke-width:2px,color:#ede9fe
    classDef external fill:#4a1535,stroke:#f472b6,stroke-width:2px,color:#fce7f3
    classDef prod fill:#1e293b,stroke:#94a3b8,stroke-width:2px,color:#cbd5e1,stroke-dasharray:5 3
    style Dev fill:#0b1220,stroke:#334155,color:#94a3b8
    style WEB fill:#0c2a3f,stroke:#1e4e6b,color:#bae6fd
```

**Servicios realmente usados:** `web`, `api`, `worker`, `postgres` (imagen `pgvector/pgvector:pg17`),
`minio`. **Nginx existe solo en producción** (`docker-compose.prod.yml`) como terminador TLS/reverse
proxy; en desarrollo no hay nginx y el proxy de Next.js cumple ese rol para `/api/v1/*`.

**Dependencias de código compartidas (no son servicios):**

- `packages/rc7_shared_db/` define una sola vez la `Base` ORM, los tipos
  cross-dialect, los modelos `Manual`/`ManualChunk`/`ManualChunkReview`/
  `ManualReviewSummary` y las migraciones idempotentes (`ensure_manual_columns`).
- `packages/rc7_shared_config/` define `SharedSettings`: la configuración que ambos
  servicios necesitan (Postgres, MinIO, modelos y timeout de Gemini) y las
  validaciones de secretos en producción. Los `Settings` de `api` y `worker`
  heredan de él y declaran solo sus campos propios.
- `packages/rc7_shared_storage/` define `ManualStorageService`: el cliente MinIO
  (subir, descargar y borrar el PDF de un manual). Los `storage.py` de `api` y
  `worker` son re-exports que le inyectan el `settings` de su servicio.

`api` y `worker` instalan los tres paquetes editable en sus imágenes.

---

## 2. Pipeline de ingestión (worker)

Implementación real en [jobs/ingestion.py](../../apps/worker/src/jobs/ingestion.py).

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontFamily':'ui-sans-serif, system-ui','fontSize':'14px','lineColor':'#94a3b8'},'flowchart':{'curve':'basis','nodeSpacing':40,'rankSpacing':45}}}%%
flowchart TD
    A["Admin: POST /api/v1/manuals (PDF)"]:::io --> B["MinIO upload + INSERT manual\nstatus=pending"]:::process
    B --> C["Worker loop · polling ~5s\nclaim_next_pending_manual()\nSELECT FOR UPDATE SKIP LOCKED → processing"]:::process
    C --> D["storage.download_manual() desde MinIO"]:::process
    D --> E["extract_pdf_text_by_page()\npypdf, por página"]:::process
    E --> E2["extract_page_sections()\noutline del PDF → sección por página\n{} si el PDF no trae outline"]:::process
    E2 --> F{"¿texto útil?"}:::decision
    F -- No --> Z1["status=failed\nlast_error='No se pudo extraer texto util...'"]:::danger
    F -- Sí --> G["build_text_chunks()\nestructural: párrafos por página, max 1200 chars\nanota section_title sin alterar los cortes"]:::process
    G --> H{"¿manual elegible?\nidioma ∈ es,en y filtro de título"}:::decision
    H -- No --> K["sin revisiones"]:::note
    H -- Sí --> I["select_chunks_for_semantic_review()\nsample_rate=1.0 ⇒ TODOS\ntoo_short / too_long / suspicious / sampled"]:::process
    I --> J["GeminiSemanticReviewer.review_chunk()\n1 llamada Gemini (SDK) por chunk\ncoherence/completeness/boundary + action"]:::gemini
    J --> L["apply_safe_chunk_autofixes()\nmerge_with_next / split / regenerate\nregenerate: reescribe con Gemini → antes del embedding"]:::gemini
    K --> L
    L --> M["embed_texts() · gemini-embedding-2\n1 types.Content por chunk · 3072 dims · batch=100"]:::gemini
    M --> N["index_manual_chunks(): DELETE previos +\nINSERT manual_chunks (embedding vector(3072))\n+ reviews + review_summary"]:::data
    N --> O["status=indexed · chunk_count · indexed_at"]:::ok
    C -. "timeout dinámico excedido" .-> Z2["status=failed (timeout)"]:::danger
    C -. "crash / reinicio" .-> R["recover_stuck_processing_manuals()\nmarca '[crash]'; tras 3 ⇒ failed"]:::danger

    classDef io fill:#0f172a,stroke:#e2e8f0,stroke-width:2px,color:#f1f5f9
    classDef process fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#e2e8f0
    classDef decision fill:#422006,stroke:#f59e0b,stroke-width:2px,color:#fde68a
    classDef gemini fill:#4a1535,stroke:#f472b6,stroke-width:2px,color:#fce7f3
    classDef data fill:#2e1065,stroke:#a78bfa,stroke-width:2px,color:#ede9fe
    classDef danger fill:#450a0a,stroke:#f87171,stroke-width:2px,color:#fee2e2
    classDef ok fill:#052e16,stroke:#4ade80,stroke-width:2px,color:#dcfce7
    classDef note fill:#1e293b,stroke:#475569,stroke-width:1px,color:#cbd5e1,stroke-dasharray:4 3
```

Notas reales: la revisión es **exhaustiva** por defecto (`SEMANTIC_REVIEW_SAMPLE_RATE=1.0`, sin tope);
el autofix `regenerate` **sí** está implementado (reescribe el chunk con Gemini, gated por
`SEMANTIC_REVIEW_REGENERATE_MAX_COHERENCE`, fail-safe a `keep`); tanto la revisión como el embedding
usan el **SDK `google-genai`**.

---

## 3. Pipeline de consulta RAG (4 fases)

Implementación real en [chat/service.py](../../apps/api/src/services/chat/service.py).

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontFamily':'ui-sans-serif, system-ui','fontSize':'14px','lineColor':'#94a3b8'},'flowchart':{'curve':'basis','nodeSpacing':40,'rankSpacing':45}}}%%
flowchart TD
    Q["POST /api/v1/chat/generate (ChatRequest)"]:::io --> P1["Fase 1 — HyDE\n_call_gemini() prosa, sin contexto\nsystem=_PHASE1_SYSTEM"]:::phase
    P1 --> P2["Fase 2 — Embed + Retrieve\n_embed_query('task: search result | query: '+prompt+HyDE[:600])\n_retrieve_chunks()"]:::phase
    P2 --> R1["pgvector · ORDER BY embedding::halfvec(3072) &lt;=&gt; query\nLIMIT 50 (HNSW)"]:::data
    R1 --> R2["re-rank Python:\nscore = (1-distancia) · hardware_factor · category_factor\ntop_k (default 24)"]:::data
    R2 --> P3["Fase 3 — Contexto\nfragmentos etiquetados [S1],[S2]… hasta budget chars\nsource_map: SID → (manual, página)"]:::phase
    P3 --> P4["Fase 4 — Generación final\n_call_gemini(force_json=True)\nsystem=_build_system_prompt (reglas PAC + trazabilidad)"]:::phase
    P4 --> PARSE["_finalize_response() — post-proceso determinista:\n1. _parse_gemini_json (repara truncados y basura tras el JSON)\n2. _lint_pac_code (reescribe MOVE J, J(...)…)\n3. _resolve_references (descarta IDs alucinados · fallback al set recuperado)\n4. _prepend_source_legend (leyenda de fuentes en el .pac)\n5. _pac_advisories (avisos semánticos, no reescriben)"]:::process
    PARSE --> OUT["JSON: summary · pac_code (con ' fuente: SX) · references · advisories"]:::process
    OUT --> SSE{"ENABLE_STREAMING?"}:::decision
    SSE -- "true" --> S1["SSE: chunk* → done\npersistir historial + audit CHAT_QUERY"]:::ok
    SSE -- "false" --> S2["único evento done\nsync; 503 si falla"]:::ok

    classDef io fill:#0f172a,stroke:#e2e8f0,stroke-width:2px,color:#f1f5f9
    classDef phase fill:#0b3d5c,stroke:#38bdf8,stroke-width:2px,color:#e0f2fe
    classDef data fill:#2e1065,stroke:#a78bfa,stroke-width:2px,color:#ede9fe
    classDef process fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#e2e8f0
    classDef decision fill:#422006,stroke:#f59e0b,stroke-width:2px,color:#fde68a
    classDef ok fill:#052e16,stroke:#4ade80,stroke-width:2px,color:#dcfce7
```

Parámetros configurables en caliente (`system_settings`), las 9 claves de `DEFAULT_SETTINGS`:
`rag_top_k_chunks` (24), `rag_context_budget_chars` (32000), `rag_candidate_pool` (50),
`gemini_temperature` (0.7), `hyde_temperature` (0.0 — solo la Fase 1: su salida alimenta el
embedding de búsqueda y no se muestra, así que no comparte la temperatura de generación),
`gemini_max_tokens` (8192), `gemini_timeout_seconds` (300), `system_prompt_pac` y
`history_max_entries` (50). Los modelos Gemini se configuran por entorno
(`GEMINI_GEN_MODEL`, `GEMINI_EMBED_MODEL`), centralizados en
`packages/rc7_shared_config`.

---

## 4. Almacenamiento y recuperación vectorial

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontFamily':'ui-sans-serif, system-ui','fontSize':'14px','lineColor':'#94a3b8'},'flowchart':{'curve':'basis','nodeSpacing':40,'rankSpacing':55}}}%%
flowchart LR
    subgraph Write["✍️ Escritura · worker"]
        W1["embed_texts()\ngemini-embedding-2 · 3072 dims"]:::gemini --> W2["manual_chunks.embedding\ncolumna vector(3072)"]:::data
    end
    subgraph Schema["🗃️ Esquema · init.py"]
        X1["CREATE EXTENSION vector"]:::data --> X2["columna vector(3072)\nDROP+ADD idempotente"]:::data
        X2 --> X3["índice HNSW sobre\n(embedding::halfvec(3072)) halfvec_cosine_ops"]:::data
    end
    subgraph Read["🔎 Lectura · API"]
        R1["_embed_query(prefijo + query)"]:::gemini --> R2["ORDER BY embedding::halfvec(3072) &lt;=&gt; q::halfvec(3072)\nLIMIT 50"]:::data
        R2 --> R3["re-rank: similitud · hardware · categoría → top_k"]:::process
    end
    W2 --- X2
    X3 -. acelera .-> R2

    classDef gemini fill:#4a1535,stroke:#f472b6,stroke-width:2px,color:#fce7f3
    classDef data fill:#2e1065,stroke:#a78bfa,stroke-width:2px,color:#ede9fe
    classDef process fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#e2e8f0
    style Write fill:#0b1a14,stroke:#1f6f52,color:#86efac
    style Schema fill:#160c2e,stroke:#5b3aa6,color:#c4b5fd
    style Read fill:#0c1f2e,stroke:#1e5a7a,color:#93c5fd
```

`halfvec`: pgvector limita los índices HNSW de `vector` a 2000 dims; para 3072 se indexa y consulta
vía cast a `halfvec(3072)`. La similitud = `1 − distancia_coseno (<=>)`.

---

## 5. Autenticación y auditoría

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontFamily':'ui-sans-serif, system-ui','fontSize':'14px','lineColor':'#94a3b8'},'flowchart':{'curve':'basis','nodeSpacing':40,'rankSpacing':50}}}%%
flowchart TD
    L["POST /auth/login (email+password)"]:::io --> V{"verify_password (Argon2/pwdlib)\n& is_active"}:::decision
    V -- No --> F["401 + audit AUTH_FAILED"]:::danger
    V -- Sí --> T["JWT HS256 firmado (sub,email,role,available_roles)\nSet-Cookie rc7_session · HttpOnly · SameSite=lax"]:::backend
    T --> AUD["audit AUTH_LOGIN"]:::audit
    REQ["Request protegido"]:::io --> GC["get_current_user()\nlee cookie → decode JWT → carga User"]:::backend
    GC -->|inválido/inactivo| E401["401"]:::danger
    GC -->|admin route| GA{"get_current_admin_user()\nrol activo == admin?"}:::decision
    GA -->|no| E403["403"]:::danger
    subgraph Audit["🛡️ audit_service.log_event() · best-effort"]
        AE["INSERT audit_log\ncaptura toda excepción → logger · nunca relanza"]:::data
    end
    AUD --> AE
    F --> AE

    classDef io fill:#0f172a,stroke:#e2e8f0,stroke-width:2px,color:#f1f5f9
    classDef decision fill:#422006,stroke:#f59e0b,stroke-width:2px,color:#fde68a
    classDef backend fill:#0f3d2e,stroke:#34d399,stroke-width:2px,color:#d1fae5
    classDef danger fill:#450a0a,stroke:#f87171,stroke-width:2px,color:#fee2e2
    classDef audit fill:#1e293b,stroke:#94a3b8,stroke-width:2px,color:#e2e8f0
    classDef data fill:#2e1065,stroke:#a78bfa,stroke-width:2px,color:#ede9fe
    style Audit fill:#0f172a,stroke:#475569,color:#cbd5e1
```

**Estado real:** Google SSO **no implementado** (`/auth/providers` solo informa). Hashing con
**Argon2** (`pwdlib.recommended()`), no bcrypt. El audit nunca rompe el flujo principal. Observabilidad =
audit_log + logs rotados a archivo (`api.log` / `worker.log`).

---

## 6. Diagrama de secuencia — Vida de una consulta

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontFamily':'ui-sans-serif, system-ui','fontSize':'14px','actorBkg':'#0f3d2e','actorBorder':'#34d399','actorTextColor':'#d1fae5','actorLineColor':'#475569','signalColor':'#94a3b8','signalTextColor':'#cbd5e1','labelBoxBkgColor':'#1e293b','labelBoxBorderColor':'#475569','labelTextColor':'#e2e8f0','loopTextColor':'#fde68a','activationBkgColor':'#0b3d5c','activationBorderColor':'#38bdf8','sequenceNumberColor':'#0f172a'}}}%%
sequenceDiagram
    autonumber
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
    A->>DB: ORDER BY embedding (distancia coseno) LIMIT 50
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
%%{init: {'theme':'base','themeVariables':{'fontFamily':'ui-sans-serif, system-ui','fontSize':'14px','actorBkg':'#4a2f0a','actorBorder':'#fbbf24','actorTextColor':'#fef3c7','actorLineColor':'#475569','signalColor':'#94a3b8','signalTextColor':'#cbd5e1','labelBoxBkgColor':'#1e293b','labelBoxBorderColor':'#475569','labelTextColor':'#e2e8f0','loopTextColor':'#fde68a','altTextColor':'#fde68a','activationBkgColor':'#2e1065','activationBorderColor':'#a78bfa','sequenceNumberColor':'#0f172a'}}}%%
sequenceDiagram
    autonumber
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
            Wk->>G: review_chunk (SDK)
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

Relaciones con **FK declarada** = líneas sólidas. Referencias lógicas (columna `int` sin
`ForeignKey`) se documentan en nota, no como relación: `chat_history.user_id`,
`audit_log.actor_id` y `manuals.uploaded_by_user_id` están indexadas;
`system_settings.updated_by` **no** lo está (es la única de las cuatro sin índice, y no se
filtra por ella).

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontFamily':'ui-sans-serif, system-ui','fontSize':'13px','lineColor':'#94a3b8','primaryColor':'#1e293b','primaryBorderColor':'#475569','primaryTextColor':'#e2e8f0','attributeBackgroundColorOdd':'#0f172a','attributeBackgroundColorEven':'#16233a'}}}%%
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
        string section_title "outline del PDF, nullable"
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

`MANUALS`, `MANUAL_CHUNKS`, `MANUAL_CHUNK_REVIEWS` y `MANUAL_REVIEW_SUMMARIES` se definen **una sola
vez** en el paquete compartido `packages/rc7_shared_db/` (Base + tipos cross-dialect incluidos), del
que dependen API y worker; las demás tablas (`USERS`, `ROLE_PERMISSIONS`, `SYSTEM_SETTINGS`,
`AUDIT_LOG`, `CHAT_HISTORY`) son propias de la API. `ROLE_PERMISSIONS`, `SYSTEM_SETTINGS` y
`AUDIT_LOG` no tienen FKs declaradas.
