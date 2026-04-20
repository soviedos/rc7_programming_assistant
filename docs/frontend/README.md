# Frontend

## Objetivo

El frontend debe comportarse como una herramienta de ingeniería asistida, no como un chat genérico. La interfaz separa acceso, trabajo operativo y administración bajo una misma identidad visual.

## Rutas actuales

### `/`

Pantalla de login con:

- correo autorizado
- contraseña
- opción para mostrar u ocultar contraseña
- validación amigable
- acceso visual reservado para Google SSO futuro

### `/app`

Workspace principal con:

- configuración del robot en sidebar izquierdo
- conversación y código PAC en panel central
- referencias e historial en sidebar derecho

### `/admin`

Consola administrativa con:

- resumen operativo
- usuarios autorizados en modo visual
- parámetros de Gemini en modo visual
- base documental en modo visual

## Criterios de diseño

- mismo lenguaje visual entre login, workspace y administración
- navegación resuelta por sesión, no por credenciales hardcodeadas en la UI
- layout adaptable
- foco en legibilidad del código PAC
