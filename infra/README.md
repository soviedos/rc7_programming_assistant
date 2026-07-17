# Infraestructura

Configuración de infraestructura y servicios de soporte para el entorno contenedorizado del RC7 Programming Assistant.

---

## Estructura

| Directorio | Contenido |
|---|---|
| [`docker/`](./docker/) | Dockerfiles para cada servicio de la aplicación |
| [`nginx/`](./nginx/) | Configuración del reverse proxy |
| [`minio/`](./minio/) | Documentación del object storage local (S3-compatible). El bucket lo crea `ensure_bucket` en `rc7_shared_storage` |
| [`postgres/`](./postgres/) | Documentación de la base de datos. **No contiene scripts**: la inicialización (extensión `vector`, tablas, índice HNSW y seeds) es Python, en [`apps/api/src/db/init.py`](../apps/api/src/db/init.py) |

## Orquestación

Los servicios se orquestan desde dos archivos en la raíz: `docker-compose.yml` (desarrollo) y
`docker-compose.prod.yml` (producción, el único que incluye `nginx`).

Llevan healthcheck `web`, `api`, `postgres` y `minio`; **`worker` no expone ninguno** — es un
proceso de polling sin puerto que atender, así que `--wait` no espera por él. Las dependencias
entre servicios sí son declarativas (`depends_on` con `condition: service_healthy`).
