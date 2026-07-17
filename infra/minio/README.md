# MinIO

Documentación del object storage local compatible con S3, utilizado para almacenar los
manuales PDF originales.

---

## Acceso local

Solo en desarrollo: en `docker-compose.prod.yml` estos puertos son `expose`, no se publican.

| Interfaz | URL |
|---|---|
| API (S3) | http://localhost:9000 |
| Console | http://localhost:9001 |

## Bucket principal

- `rc7-manuals`: los PDFs originales, y solo eso. `ManualStorageService` únicamente sube,
  descarga y borra el PDF de un manual: los derivados del pipeline (chunks, embeddings,
  revisiones) viven en PostgreSQL, no aquí.

El bucket lo crea `ensure_bucket()` en `rc7_shared_storage`; no hay que provisionarlo a mano.
