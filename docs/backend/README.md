# Backend

Documentación técnica del backend del RC7 Programming Assistant, construido con FastAPI.

---

## Contenido

| Documento | Descripción |
|---|---|
| [api-modules.md](./api-modules.md) | Módulos implementados, parciales y planificados de la API |

## Alcance

Esta sección cubre:

- Contratos de la API REST y sus esquemas de request/response
- Módulos de negocio y sus responsabilidades
- Flujos de autenticación y gestión de sesiones
- Servicios de retrieval y generación de respuestas (planificado)
- Estrategia de validación y manejo de errores

## Rol del backend

El backend es el punto central de control del sistema: toda autenticación, autorización, orquestación de servicios y acceso a datos pasa por él. El frontend y el worker se comunican exclusivamente a través de sus contratos.
