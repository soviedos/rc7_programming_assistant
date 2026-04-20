# Workspace Principal

## Objetivo

El workspace debe comportarse como un entorno de apoyo tecnico, no como un chat casual.

## Layout actual

### Sidebar izquierdo

- seleccion de robot
- numero de ejes
- configuracion IO
- opciones de vision
- perfil de aplicacion

### Panel central

- prompt del usuario
- respuesta tecnica
- bloque de codigo PAC
- botones de copia

### Sidebar derecho

- historial de consultas
- referencias a manuales
- paginas citadas
- fragmentos usados en retrieval
- herramientas de apoyo

## Estado de implementación

El layout ya está construido e integrado con rutas protegidas, pero el contenido técnico todavía usa varios datos de ejemplo mientras se conecta el backend real de chat, administración y RAG.

## Justificacion

Esta composicion obliga al usuario y al sistema a trabajar con contexto tecnico explicito.
