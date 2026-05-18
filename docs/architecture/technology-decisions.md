# Decisiones Tecnológicas

Resumen de tecnologías seleccionadas y decisiones de arquitectura (ADRs) del proyecto.

---

## Stack base

### Frontend — Next.js 14

| Criterio | Detalle |
|---|---|
| **App Router** | Layouts anidados, rutas protegidas y separación clara entre landing, workspace y administración |
| **TypeScript** | Tipado estático end-to-end con los contratos de la API |
| **Tailwind CSS** | Utilidades de estilo sin archivos CSS separados |
| **Proxy interno** | Todas las llamadas a `/api/v1/*` se enrutan al backend interno, evitando CORS en producción |

### Backend — FastAPI

| Criterio | Detalle |
|---|---|
| **Rendimiento** | Framework ASGI de alto rendimiento con soporte nativo de streaming (StreamingResponse) |
| **Pydantic v2** | Validación automática de request/response con modelos tipados |
| **Documentación** | Swagger UI y ReDoc generados automáticamente desde los tipos |
| **Ecosistema IA** | Compatibilidad directa con google-genai SDK y SQLAlchemy + pgvector |

### Worker — Python independiente

| Criterio | Detalle |
|---|---|
| **Aislamiento** | Proceso separado para parsing y embedding pesado; no bloquea requests HTTP |
| **Coordinación** | Polling a PostgreSQL con `SELECT ... FOR UPDATE SKIP LOCKED` — sin broker externo |
| **Resiliencia** | Timeout por manual, recuperación de estados `processing` al reiniciar |

### Base de datos — PostgreSQL 15 + pgvector

| Criterio | Detalle |
|---|---|
| **Unificación** | Datos transaccionales y vectores en una sola instancia |
| **Sin complejidad extra** | No se requiere un vector DB dedicado al volumen actual |
| **Extensión pgvector** | Columna `embedding REAL[]` + búsqueda coseno directamente en SQL |

### Object storage — MinIO

| Criterio | Detalle |
|---|---|
| **Compatibilidad S3** | Migración futura a AWS S3 / GCS sin cambios de código |
| **Desarrollo local** | Contenedor ligero sin dependencia de proveedores cloud |

### Cache y colas — Redis

| Criterio | Detalle |
|---|---|
| **Versatilidad futura** | Soporta colas, cache y pub/sub en un solo servicio |
| **Estado actual** | Presente en el stack pero sin consumidores activos; el worker usa polling SQL |

---

## Architecture Decision Records (ADR)

### ADR-001 — pgvector en PostgreSQL en lugar de vector DB dedicado

**Contexto:** El sistema necesita almacenamiento y búsqueda de embeddings para el pipeline RAG.

**Decisión:** Usar la extensión pgvector sobre PostgreSQL 15 en lugar de una base de datos
vectorial dedicada (Pinecone, Weaviate, Qdrant, etc.).

**Razonamiento:**
- El volumen inicial de manuales DENSO RC7 es pequeño (decenas de documentos).
- Una sola instancia de PostgreSQL elimina la complejidad operativa de mantener dos bases de datos.
- pgvector soporta similitud coseno eficientemente para los volúmenes proyectados.
- La migración a un vector DB dedicado es posible si el volumen crece, sin cambios de esquema
  en las tablas transaccionales.

**Consecuencias:** La búsqueda vectorial escala linealmente con el número de chunks. Se aplica
un `LIMIT 5000` en el scan para proteger memoria. Un índice HNSW puede añadirse si el volumen lo requiere.

---

### ADR-002 — HyDE (Hypothetical Document Embeddings) para retrieval

**Contexto:** El embedding de la consulta del usuario frecuentemente no tiene similitud alta con
fragmentos de manuales técnicos, porque la pregunta y la respuesta están en espacios semánticos distintos.

**Decisión:** Usar HyDE: Gemini genera una respuesta hipotética a la consulta (Fase 1), luego
se embebe `(consulta + primeros 600 chars de respuesta hipotética)` para el retrieval.

**Razonamiento:**
- Las respuestas hipotéticas están en el mismo dominio semántico que los manuales (terminología técnica PAC).
- HyDE mejora la precisión de retrieval en dominios técnicos sin requerir fine-tuning del modelo de embedding.
- El costo adicional (una llamada extra a Gemini) es aceptable dado el contexto de uso.

**Consecuencias:** Cada query al chat realiza dos llamadas a Gemini (HyDE + respuesta final con RAG)
más una llamada al modelo de embedding.

---

### ADR-003 — SSE (Server-Sent Events) en lugar de WebSocket para streaming

**Contexto:** El pipeline RAG tarda entre 10-60 segundos. Se necesita streaming de la respuesta
para mejorar la experiencia de usuario.

**Decisión:** Usar `StreamingResponse` de FastAPI con `Content-Type: text/event-stream` (SSE)
en lugar de WebSocket.

**Razonamiento:**
- El endpoint de generación es `POST` (necesita enviar el payload JSON con la config del robot).
- `EventSource` del browser es GET-only; SSE sobre POST requiere `fetch()` con `ReadableStream`, que es
  lo que implementa el frontend.
- SSE es unidireccional (servidor → cliente), suficiente para este caso de uso.
- WebSocket requeriría gestionar conexiones bidireccionales y reconexión, añadiendo complejidad innecesaria.
- Nginx configurado con `proxy_buffering off` y `proxy_read_timeout 310s` para la ruta `/api/v1/chat/`.

**Consecuencias:** El cliente implementa un lector de `ReadableStream` con decodificación de líneas SSE.
Eventos: `chunk` (texto parcial), `done` (JSON final), `error` (fallo del pipeline). La historia y el
audit log se persisten dentro del generator después de emitir el evento `done`.

---

### ADR-004 — Parámetros del pipeline en DB en lugar de variables de entorno

**Contexto:** Los parámetros de Gemini (temperatura, max_tokens, top-k RAG, prompt de sistema)
necesitan ser ajustados frecuentemente durante la puesta a punto del asistente.

**Decisión:** Almacenar estos parámetros en la tabla `system_settings` con una interfaz CRUD
administrativa, en lugar de usar variables de entorno.

**Razonamiento:**
- Los cambios de env vars requieren reinicio del contenedor; los cambios en DB son inmediatos.
- El sistema de settings es auto-seeded con valores por defecto al arrancar.
- Los parámetros son legibles y auditables desde la consola de administración.
- El endpoint `POST /reset` permite restaurar todos los valores por defecto en un clic.

**Consecuencias:** Cada request al pipeline RAG realiza varias lecturas de `system_settings`.
El overhead es despreciable para el volumen actual (SQLAlchemy pooled connections).

---

### ADR-005 — Audit log que nunca lanza excepción

**Contexto:** El sistema necesita registro de eventos para trazabilidad y seguridad, pero el
registro no debe interrumpir el flujo principal si falla (ej. DB temporalmente no disponible).

**Decisión:** `log_event()` captura todas las excepciones internamente y las registra en el
logger Python (`_logger.error()`), nunca re-lanza.

**Razonamiento:**
- La observabilidad es un requisito secundario: un fallo de auditoría no debe degradar la
  experiencia del usuario ni romper una transacción de negocio.
- Los errores de audit son registrados en el log del proceso para diagnóstico.
- El patrón "best-effort audit" es estándar en sistemas que priorizan disponibilidad.

**Consecuencias:** En caso de fallo del audit log, el evento se pierde silenciosamente (solo
queda en el log del proceso). No hay reintentos ni cola de eventos.
