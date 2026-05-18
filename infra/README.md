# Infraestructura

Configuración de infraestructura y servicios de soporte para el entorno contenedorizado del RC7 Programming Assistant.

---

## Estructura

| Directorio | Contenido |
|---|---|
| [`docker/`](./docker/) | Dockerfiles para cada servicio de la aplicación |
| [`nginx/`](./nginx/) | Configuración del reverse proxy |
| [`minio/`](./minio/) | Configuración del object storage local (S3-compatible) |
| [`postgres/`](./postgres/) | Scripts de inicialización y configuración de la base de datos |

## Orquestación

Todos los servicios se orquestan desde el archivo `docker-compose.yml` en la raíz del proyecto. Cada servicio tiene healthchecks configurados y dependencias declarativas.
