# Estructura interna del frontend

## `app/`

Aqui viviran las rutas principales:

- landing
- login
- workspace
- admin

## `components/`

Componentes reutilizables y presentacionales.

Se separan de `features/` para no mezclar piezas visuales con logica de negocio.

## `features/`

Modulos funcionales del producto, por ejemplo:

- autenticacion
- historial
- workspace de prompts
- referencias documentales
- configuracion de robot

## `lib/`

Clientes HTTP, helpers de formateo, manejo de tokens y utilidades transversales del cliente.

## `styles/`

Estilos globales y tokens visuales.

## `types/`

Tipos TypeScript compartidos por toda la app web.
