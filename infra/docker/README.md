# Docker

Dockerfiles para los servicios de la aplicación.

---

## Archivos

| Archivo | Servicio | Descripción |
|---|---|---|
| `api.Dockerfile` | Backend | FastAPI con Python 3.12+ |
| `web.Dockerfile` | Frontend | Next.js con Node.js |
| `worker.Dockerfile` | Worker | Python 3.12+ para pipeline documental |

## Construcción

Los Dockerfiles se referencian desde `docker-compose.yml` y se construyen automáticamente con:

```bash
docker compose up --build -d
```
