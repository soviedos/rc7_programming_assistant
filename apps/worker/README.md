# Worker

Proceso asincrónico del sistema.

## Estado actual

Hoy funciona como base placeholder para el pipeline documental, manteniendo el lugar arquitectónico correcto sin ejecutar todavía ingestión real.

## Responsabilidades objetivo

- ingesta de PDFs
- parsing y limpieza
- chunking semántico
- clasificación por robot y controlador
- embeddings
- indexación en PostgreSQL + pgvector

## Pruebas

```bash
docker compose exec worker python -m pytest
```
