# API

Backend principal en `FastAPI`.

## Responsabilidades actuales

- autenticación con correo y contraseña
- sesión por cookie firmada
- cambio de rol activo
- bootstrap admin desde variables de entorno
- contratos base para chat y administración

## Responsabilidades futuras

- CRUD administrativo de usuarios
- integración con Gemini
- retrieval sobre manuales indexados
- configuración administrativa persistente
- auditoría operativa

## Pruebas

```bash
docker compose exec api python -m pytest
```
