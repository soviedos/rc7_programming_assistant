# Nginx

Configuración del reverse proxy para servir frontend y backend bajo un punto de entrada común.

---

## Estado

Pendiente de implementación. Se utilizará cuando el proyecto requiera un dominio unificado o terminación TLS en el entorno de despliegue.

## Uso previsto

- Proxy inverso para `web` (`:3000`) y `api` (`:8000`)
- Terminación TLS
- Compresión de assets estáticos
- Headers de seguridad
