# Decisiones Tecnologicas

## Next.js para frontend

Se eligio por:

- buena experiencia de desarrollo en VS Code
- rutas y layouts modernos
- facilidad para construir una landing y un workspace en una sola app
- integracion natural con TypeScript

## FastAPI para backend

Se eligio por:

- soporte excelente para Python
- tipado y validacion
- facilidad para documentar APIs
- buena integracion con servicios de IA y pipelines de backend

## Worker Python separado

Se eligio por:

- necesidad de parsing y chunking pesado
- posibilidad de reindexacion
- menor riesgo de bloquear requests web

## PostgreSQL + pgvector

Se eligio por:

- una sola base para datos transaccionales y vectores
- menor complejidad operativa
- soporte adecuado para el volumen inicial de manuales

## MinIO

Se eligio para el stack local contenedorizado por:

- compatibilidad tipo S3
- despliegue simple en contenedor
- independencia de proveedores cloud en desarrollo

## Redis

Se eligio por:

- simplicidad
- soporte de colas y cache
- adopcion amplia en ecosistemas Python
