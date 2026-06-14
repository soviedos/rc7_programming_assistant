# PostgreSQL

Configuración de la base de datos principal del sistema.

---

## Acceso local

| Parámetro | Valor por defecto |
|---|---|
| Host | `localhost` |
| Puerto | `5432` |
| Base de datos | `rc7_assistant` |
| Usuario | `postgres` |
| Contraseña | Definida en `.env` |

## Extensiones

- **pgvector** (activa): almacenamiento y búsqueda de embeddings vectoriales. La imagen es
  `pgvector/pgvector:pg17`; `init.py` ejecuta `CREATE EXTENSION IF NOT EXISTS vector` al arrancar.
  La columna `manual_chunks.embedding` es `vector(3072)`, con un índice **HNSW** construido sobre
  un cast a `halfvec(3072)` (`halfvec_cosine_ops`) — pgvector limita los índices HNSW de `vector`
  a 2000 dimensiones, por lo que para 3072 se indexa vía `halfvec`. La búsqueda ordena por
  distancia coseno con el operador `<=>`.

## Contenido

Esta carpeta contendrá scripts de inicialización, configuraciones locales y soporte para extensiones.
