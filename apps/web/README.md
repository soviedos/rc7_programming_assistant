# Web — Frontend Next.js

Aplicación frontend del RC7 Programming Assistant, responsable de la experiencia de usuario completa.

---

## Stack técnico

| Tecnología | Uso |
|---|---|
| Next.js | Framework React con App Router |
| React | Librería de UI |
| TypeScript | Tipado estático |
| Vitest | Framework de testing |
| Testing Library | Testing de componentes |

---

## Responsabilidades implementadas

- Login con validación amigable y mensajes de error claros
- Navegación protegida por sesión y rol activo
- Workspace principal del asistente con layout de tres paneles
- Consola administrativa con vistas de resumen
- Cambio de rol desde el perfil de sesión

## Responsabilidades planificadas

- Autenticación con Google SSO
- Integración con el backend de chat y RAG
- CRUD administrativo de usuarios
- Gestión de la base documental desde la consola

---

## Rutas

| Ruta | Descripción |
|---|---|
| `/` | Login |
| `/app` | Workspace del asistente |
| `/admin` | Consola administrativa |

---

## Pruebas

```bash
docker compose exec web npm test
```
