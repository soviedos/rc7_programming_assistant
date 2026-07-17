# Workspace Principal

## Objetivo

El workspace se diseña como un **entorno de apoyo técnico estructurado**, no como una interfaz de
chat casual. La disposición obliga tanto al usuario como al sistema a trabajar con contexto técnico
explícito.

---

## Layout

Tres columnas, montadas en [`app/chat/page.tsx`](../../apps/web/src/app/chat/page.tsx):

```text
┌──────────────────┬───────────────────────────┬──────────────────┐
│  SIDEBAR IZQ.    │     PANEL CENTRAL         │  SIDEBAR DER.    │
│  HistorySidebar  │     CanvasPanel           │  AiChatSidebar   │
│                  │                           │                  │
│  Configuración   │  Pestañas: Código /       │  Interacciones:  │
│  del robot:      │  Troubleshooting /        │  prompt y        │
│                  │  Entrenamiento            │  respuesta       │
│  • Modelo        │                           │                  │
│  • Controladora  │  Último código PAC        │  Fuentes:        │
│  • Payload       │  generado                 │  S1 — manual,    │
│  • Config. IO    │                           │  pág. N          │
│  • Tipo de mano  │  [Copiar código]          │                  │
│  • Instalación   │                           │  Historial de    │
│  • Herramienta   │  Barra de input           │  consultas       │
│  • Velocidad máx.│                           │                  │
└──────────────────┴───────────────────────────┴──────────────────┘
```

> El nombre `HistorySidebar` engaña: **no** contiene el historial, sino la configuración del robot
> (el propio `chat/page.tsx` lo comenta como `/* Left: Robot configuration */`). El historial real
> vive en `AiChatSidebar`, a la derecha.

### Sidebar izquierdo — Configuración del robot

Los campos son los de `ChatConfig`
([`features/chat/chat-panel.tsx`](../../apps/web/src/features/chat/chat-panel.tsx)):

| Campo | Descripción |
|---|---|
| Modelo de robot | Selección del robot DENSO (VP-6242, VS-6556, VM-6083, VS-087) |
| Controladora | Versión de la controladora (RC7) |
| Peso del manipulador | Payload en kg, acotado por el máximo del modelo |
| Configuración IO | Entradas y salidas digitales, más tarjeta de expansión opcional |
| Tipo de manipulador | Neumática simple, doble, servo… |
| Tipo de instalación | Piso, techo, pared |
| Herramienta activa | Número de tool |
| Velocidad máxima | Porcentaje de velocidad permitida |

El número de ejes **no** es un campo editable: es un dato derivado del modelo (`ROBOT_SPECS`), y hoy
los cuatro robots soportados son de 6 ejes.

### Panel central — Canvas del artefacto

- Tres modos (`WorkspaceMode`): `code`, `troubleshooting` y `training` (este último, en desarrollo).
- Muestra **solo el último** código PAC generado, no la conversación.
- El código se renderiza en monoespaciado. **No hay resaltado de sintaxis** (no hay ningún
  highlighter entre las dependencias); lo que sí se resalta son las referencias inline
  `' fuente: SX`, que enlazan cada línea con su manual y página.
- Botón de copia al portapapeles, con fallback si `navigator.clipboard` no está disponible.
- Barra de input para describir la rutina PAC.

### Sidebar derecho — Interacciones, fuentes e historial

- La **conversación**: el prompt del usuario y la respuesta del asistente.
- Las **fuentes** de la respuesta: `MessageReference` es `{ sourceId, title, page }`, así que se
  muestra el ID de trazabilidad, el título del manual y la página. El texto de los fragmentos
  recuperados **no** llega al frontend.
- El **historial** de consultas, que se puede volver a abrir.

---

## Estado de implementación

El layout está construido e integrado con rutas protegidas. El pipeline RAG con Gemini es
funcional: el sidebar izquierdo envía la configuración del robot como contexto, el panel central
muestra el código generado, y el sidebar derecho muestra la conversación con las referencias a los
manuales recuperados y el historial.

## Justificación

Esta composición garantiza que cada consulta al asistente incluya el contexto técnico del robot
configurado, evitando respuestas genéricas que no apliquen al hardware específico del usuario.
