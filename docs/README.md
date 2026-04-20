# Documentación

La documentación del proyecto se organiza para explicar:

- qué existe hoy
- por qué se eligió esa solución
- cómo se ejecuta y cómo se valida

## Índice recomendado

- `architecture/`: arquitectura general, estructura y decisiones técnicas.
- `backend/`: contratos API, autenticación y responsabilidades del backend.
- `frontend/`: rutas, layout y criterios de experiencia de usuario.
- `rag/`: estrategia de ingestión documental y filtrado técnico.
- `operations/`: arranque local, operación y pruebas.
- `decisions/`: ADRs y decisiones puntuales.

## Regla de mantenimiento

Si cambia autenticación, arquitectura, UI, operación o testing, esta carpeta debe actualizarse en la misma iteración.
