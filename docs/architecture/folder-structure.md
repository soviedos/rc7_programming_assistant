# Estructura de Carpetas

## Objetivo

La estructura se definio para que cualquier desarrollador pueda abrir el proyecto en VS Code y entender rapidamente donde vive cada responsabilidad.

## Arbol principal

```text
apps/
  web/
  api/
  worker/
docs/
  architecture/
  backend/
  frontend/
  rag/
  operations/
  decisions/
infra/
storage/
```

## Explicacion por area

### `apps/web`

Aplicacion de interfaz.

#### `src/app`
Rutas, layouts y entry points de la aplicacion.

#### `src/components`
Piezas visuales reutilizables.

#### `src/features`
Agrupa codigo por funcionalidad del negocio, no por tipo tecnico.

#### `src/lib`
Helpers del frontend, clientes HTTP y utilidades compartidas.

### `apps/api/src/api/v1`

Contendra endpoints versionados.

Esto prepara el proyecto para evolucionar sin romper contratos rapidamente.

### `apps/api/src/services`

Coloca la logica de negocio en servicios y evita meter reglas complejas dentro de los endpoints.

### `apps/api/src/repositories`

Encapsula acceso a datos y mantiene el dominio desacoplado de detalles de persistencia.

### `apps/worker/src/parsers`

Parsing de PDFs y transformacion a una forma entendible por el pipeline RAG.

### `apps/worker/src/classifiers`

Dedicado a detectar aplicabilidad por robot, version y opciones.

Esta carpeta existe porque esa necesidad es central en tu producto.

### `docs`

Documentacion viva del proyecto.

Separamos documentacion tecnica por temas para que no quede enterrada en un README gigante.

### `infra`

Configuraciones de despliegue local y soporte de contenedores.

### `storage`

Persistencia local usada por MinIO o por procesos auxiliares en desarrollo.
