# Workspace Principal

## Objetivo

El workspace se diseña como un **entorno de apoyo técnico estructurado**, no como una interfaz de chat casual. La disposición obliga tanto al usuario como al sistema a trabajar con contexto técnico explícito.

---

## Layout

```text
┌──────────────────┬───────────────────────────┬──────────────────┐
│  SIDEBAR IZQ.    │     PANEL CENTRAL         │  SIDEBAR DER.    │
│                  │                           │                  │
│  Configuración   │  Prompt del usuario       │  Historial de    │
│  del robot:      │                           │  consultas       │
│                  │  Respuesta técnica        │                  │
│  • Modelo        │                           │  Referencias a   │
│  • Número ejes   │  Bloque de código PAC     │  manuales        │
│  • Config. IO    │                           │                  │
│  • Visión        │  [Copiar código]          │  Páginas citadas │
│  • Perfil app    │                           │  Fragmentos RAG  │
│                  │                           │                  │
└──────────────────┴───────────────────────────┴──────────────────┘
```

### Sidebar izquierdo — Configuración del robot

| Campo | Descripción |
|---|---|
| Modelo de robot | Selección del tipo de robot DENSO |
| Número de ejes | 4-axis, 6-axis |
| Configuración IO | Entradas/salidas digitales y analógicas |

### Panel central — Conversación y código

- Campo de prompt del usuario
- Respuesta técnica generada por el asistente
- Bloque de código PAC con resaltado de sintaxis
- Botones de copia rápida

### Sidebar derecho — Referencias y contexto

- Historial de consultas de la sesión
- Referencias a manuales utilizados en la respuesta
- Páginas y secciones citadas
- Fragmentos recuperados por el pipeline RAG

---

## Estado de implementación

El layout está construido e integrado con rutas protegidas. El pipeline RAG con Gemini es completamente funcional: el sidebar izquierdo envía la configuración del robot como contexto, el panel central muestra la respuesta generada con bloque de código PAC, y el sidebar derecho muestra el historial de consultas con referencias a los manuales recuperados.

## Justificación

Esta composición garantiza que cada consulta al asistente incluya el contexto técnico del robot configurado, evitando respuestas genéricas que no apliquen al hardware específico del usuario.
