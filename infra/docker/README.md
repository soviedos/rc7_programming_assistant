# Docker

Dockerfiles para los servicios de la aplicación.

---

## Archivos

| Archivo | Servicio | Descripción |
|---|---|---|
| `api.Dockerfile` | Backend | FastAPI con Python 3.12+ |
| `web.Dockerfile` | Frontend | Next.js (build multi-stage → salida `standalone`, `node server.js`) |
| `worker.Dockerfile` | Worker | Python 3.12+ para pipeline documental |

## Construcción

Los Dockerfiles se referencian desde `docker-compose.yml` y se construyen automáticamente con:

```bash
docker compose up --build -d
```

## Notas

- **`web.Dockerfile`** copia `package.json` **y** `package-lock.json` antes de `npm ci`
  (este último es obligatorio para `npm ci`) y produce la salida `standalone` de Next.js
  (`output: "standalone"` en `next.config.ts`), que se ejecuta con `node server.js`.
- El servicio `web` corre en **modo producción**: no monta el código fuente como volumen
  (un bind-mount taparía `/app/server.js` de la imagen). Para iterar en el frontend con
  hot-reload, usar `npm run dev` fuera de Docker o un override de `command`.

## Ejecución operativa

El flujo de desarrollo y validación del proyecto está orientado a contenedores: servicios, shells y suites de prueba deben correrse mediante `docker compose`.
