# Architecture Decision Records

Registro de decisiones técnicas relevantes del proyecto, documentadas en formato ADR (Architecture Decision Record).

---

## Decisiones registradas

Hay **dos series** por razones históricas. La numeración no es continua entre ellas
(`ADR-0001` con cuatro dígitos aquí, `ADR-00X` con tres allí): son registros distintos,
no una secuencia.

### Serie larga — un archivo por decisión

| ID | Título | Estado |
|---|---|---|
| [ADR-0001](./ADR-0001-monolithic-modular-architecture.md) | Monolito modular con frontend separado | Aprobado |

### Serie corta — en [`architecture/technology-decisions.md`](../architecture/technology-decisions.md)

| ID | Título |
|---|---|
| [ADR-001](../architecture/technology-decisions.md#adr-001-pgvector-en-postgresql-en-lugar-de-vector-db-dedicado) | pgvector en PostgreSQL en lugar de vector DB dedicado |
| [ADR-002](../architecture/technology-decisions.md#adr-002-hyde-hypothetical-document-embeddings-para-retrieval) | HyDE para retrieval |
| [ADR-003](../architecture/technology-decisions.md#adr-003-sse-server-sent-events-en-lugar-de-websocket-para-streaming) | SSE en lugar de WebSocket para streaming |
| [ADR-004](../architecture/technology-decisions.md#adr-004-parámetros-del-pipeline-en-db-en-lugar-de-variables-de-entorno) | Parámetros del pipeline en DB en lugar de variables de entorno |
| [ADR-005](../architecture/technology-decisions.md#adr-005-audit-log-que-nunca-lanza-excepción) | Audit log que nunca lanza excepción |
| [ADR-006](../architecture/technology-decisions.md#adr-006-re-ranking-por-compatibilidad-de-hardware-en-el-retrieval) | Re-ranking por compatibilidad de hardware |
| [ADR-007](../architecture/technology-decisions.md#adr-007-migración-del-espacio-de-embeddings-a-gemini-embedding-2-3072-dim) | Migración del espacio de embeddings a gemini-embedding-2 |

## Decisiones pendientes de documentación

- Versionado de prompts del sistema
- Detección de aplicabilidad técnica por tipo de robot (ADR-006 cubre el re-ranking en el
  retrieval, pero no la aplicabilidad como concepto de producto)
- Validación de código PAC antes de presentarlo al usuario (implementada — el linter
  determinista `_lint_pac_code` y los advisories — pero la decisión no está registrada)
- Estrategia de migración de base de datos (implementada como migraciones idempotentes en
  `db/init.py` y migraciones dirigidas en el seed de settings, sin ADR que lo justifique)

> "Selección del modelo Gemini y estrategia de prompts" ya **no** está pendiente: la cubren
> ADR-007 (modelo y espacio de embeddings) y ADR-004 (prompts en DB).
