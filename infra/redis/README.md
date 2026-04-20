# Redis

Configuración del servicio de cache y colas de tareas.

---

## Acceso local

| Parámetro | Valor por defecto |
|---|---|
| Host | `localhost` |
| Puerto | `6379` |

## Uso en el proyecto

| Función | Descripción |
|---|---|
| **Colas de tareas** | Coordinación entre el backend y el worker para jobs de ingestión |
| **Cache** | Almacenamiento temporal de resultados frecuentes |

## Contenido

Esta carpeta contendrá configuraciones locales y ajustes de persistencia cuando se requieran.
