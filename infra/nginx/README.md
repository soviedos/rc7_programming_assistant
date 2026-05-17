# Nginx

Configuración del reverse proxy para servir frontend y backend bajo un punto de entrada común.

---

## Estado

Implementado. Ver [`nginx.conf`](./nginx.conf).

## Funcionalidad

- HTTP → HTTPS redirect (301)
- Proxy inverso hacia `web:3000` (Next.js maneja internamente el proxy a la API)
- Terminación TLS con certificados en `infra/nginx/ssl/`
- Headers de seguridad (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- Compresión gzip para assets estáticos
- Timeout extendido (130 s) para peticiones largas del pipeline Gemini

## Uso

Incluido como servicio en `docker-compose.prod.yml`. Requiere:
- `infra/nginx/ssl/fullchain.pem`
- `infra/nginx/ssl/privkey.pem`

Ver [docs/operations/deployment.md](../../docs/operations/deployment.md) para instrucciones de obtención de certificados.
