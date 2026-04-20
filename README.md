# RC7 Programming Assistant

Aplicación web para asistir programación PAC sobre robots DENSO con controlador RC7, enfocada en producir respuestas técnicas y código listo para copiar y pegar en WinCaps III.

## Qué resuelve este proyecto

- autenticación con usuarios autorizados y sesiones persistentes
- separación de experiencia entre usuario y administrador
- base arquitectónica para RAG sobre manuales PDF DENSO
- interfaz web adaptable con identidad visual consistente
- salida orientada a programación PAC y troubleshooting

## Estado actual consolidado

### Implementado hoy

- `Frontend Next.js` con rutas:
  - `/` login
  - `/app` workspace del asistente
  - `/admin` consola administrativa
- `Backend FastAPI` con:
  - `POST /api/v1/auth/login`
  - `GET /api/v1/auth/me`
  - `POST /api/v1/auth/switch-role`
  - `POST /api/v1/auth/logout`
  - `GET /api/v1/health/`
  - `GET /api/v1/admin/status`
  - `POST /api/v1/chat/generate`
- `PostgreSQL` como persistencia real de usuarios autorizados
- `JWT por cookie HttpOnly` para sesión
- `Bootstrap admin` por variables de entorno
- stack contenedorizado con `web`, `api`, `worker`, `postgres`, `redis` y `minio`
- pruebas automatizadas para backend, frontend y worker

### Placeholder o pendiente

- Google SSO real
- CRUD administrativo real de usuarios
- integración real con Gemini
- pipeline real de ingestión y retrieval de manuales
- validación PAC real más allá de mocks visuales

## Arquitectura

La solución sigue un `monolito modular con frontend separado`:

- `apps/web`: UI, rutas protegidas y experiencia del usuario
- `apps/api`: autenticación, reglas de negocio y contratos HTTP
- `apps/worker`: procesamiento asincrónico de documentos
- `postgres + pgvector`: datos transaccionales y futura base vectorial
- `minio`: almacenamiento de PDFs y derivados
- `redis`: coordinación de trabajos y cache ligera

Esta decisión mantiene la operación simple, pero deja el sistema listo para crecer hacia RAG real.

## Estructura principal

```text
rc7_programming_assistant/
├── apps/
│   ├── api/
│   ├── web/
│   └── worker/
├── docs/
├── infra/
└── storage/
```

## Arranque local

```bash
docker compose up --build -d
```

## Servicios expuestos

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## Testing

### Backend

```bash
docker compose exec api python -m pytest
```

### Frontend

```bash
docker compose exec web npm test
```

### Worker

```bash
docker compose exec worker python -m pytest
```

## Documentación clave

- [docs/architecture/overview.md](./docs/architecture/overview.md)
- [docs/backend/api-modules.md](./docs/backend/api-modules.md)
- [docs/frontend/workspace-layout.md](./docs/frontend/workspace-layout.md)
- [docs/operations/local-development.md](./docs/operations/local-development.md)
- [docs/operations/testing.md](./docs/operations/testing.md)
- [docs/rag/manual-ingestion.md](./docs/rag/manual-ingestion.md)

## Nota operativa

Las credenciales iniciales deben vivir en variables de entorno y nunca en la interfaz. La documentación y las pruebas ya reflejan el estado real del sistema, no el scaffold original.
