# ADR-0001 — Monolito modular con frontend separado

## Estado

**Aprobado**

## Contexto

El producto requiere:

- Administración de usuarios con roles diferenciados
- Retrieval documental sobre manuales técnicos DENSO
- Generación de código PAC con respaldo de contexto verificado
- Trazabilidad de acciones administrativas y operativas
- Despliegue simple y reproducible en contenedores

Se evaluó la opción de microservicios independientes frente a un monolito modular con separación clara de responsabilidades.

## Decisión

Se adopta una arquitectura de **monolito modular** compuesta por:

- **Frontend separado** (`apps/web/`): aplicación Next.js independiente
- **Backend central** (`apps/api/`): API FastAPI con servicios organizados por dominio
- **Worker asincrónico** (`apps/worker/`): proceso dedicado al pipeline documental

Los tres componentes se despliegan como contenedores independientes, orquestados con Docker Compose.

## Justificación

- Reduce la complejidad operativa frente a microservicios distribuidos
- Mantiene fronteras claras de responsabilidad entre componentes
- Facilita la depuración y el testing al tener contexto compartido en el backend
- Permite evolucionar hacia servicios independientes si el volumen lo requiere

## Consecuencias

- **Positivas**: despliegue más simple, menor overhead de comunicación, documentación y testing más directos
- **Negativas**: el backend concentra más responsabilidades; cambios grandes pueden requerir coordinación entre módulos
- **Mitigación**: la organización en servicios, repositorios y módulos funcionales permite extraer servicios independientes en el futuro sin refactoring estructural
