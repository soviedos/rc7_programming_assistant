# Despliegue en Producción

Guía para migrar el sistema a un servidor de producción (AWS Lightsail, VPS, o servidor on-premises) conservando todos los datos existentes.

---

## Requisitos del servidor

- Linux (Ubuntu 22.04 LTS recomendado)
- Docker >= 24.0
- Docker Compose >= 2.20
- 8 GB RAM mínimo (el build de Next.js + todos los servicios consumen ~5–6 GB)
- Certificados TLS válidos para el dominio

---

## Diferencias respecto al entorno de desarrollo

| Aspecto | Desarrollo (`docker-compose.yml`) | Producción (`docker-compose.prod.yml`) |
|---|---|---|
| Código fuente (api y worker) | Montado como volumen (`./apps/…:/app` + `./packages/…`) | Copiado dentro de la imagen |
| Frontend | `next build` + `node server.js` — **igual que producción**: el servicio `web` de desarrollo también corre el build standalone y no monta el código, así que **no hay hot reload**; cada cambio exige `docker compose up --build -d web` | `next build` + `node server.js` |
| Backend | `uvicorn --reload` | `uvicorn` sin reload |
| Puertos internos | Expuestos al host (5432, 9000) | Solo accesibles en red Docker interna |
| MinIO | Bind mount `./storage/data` | Named volume `minio_data` |
| Reverse proxy | Ninguno | Nginx con HTTPS |

---

## Estructura de archivos de producción

```text
docker-compose.prod.yml   # Compose autónomo de producción
infra/nginx/nginx.conf    # Reverse proxy Nginx
infra/nginx/ssl/          # Certificados TLS (NO versionar)
scripts/export-data.sh    # Exporta datos del servidor origen
scripts/import-data.sh    # Importa datos en el servidor destino
.env.example              # Template único de variables (dev y servidor)
```

---

## Paso 1 — Preparar el `.env` de producción

En el servidor, copiar el template y rellenar todos los valores:

```bash
cp .env.example .env
```

Variables obligatorias en producción:

```env
APP_ENV=production
JWT_SECRET=<generar con: openssl rand -hex 32>
BOOTSTRAP_ADMIN_EMAIL=<email del primer administrador>
BOOTSTRAP_ADMIN_PASSWORD=<contraseña fuerte>
POSTGRES_PASSWORD=<contraseña fuerte>
MINIO_ROOT_USER=<usuario personalizado>
MINIO_ROOT_PASSWORD=<contraseña fuerte>
GEMINI_API_KEY=<clave de Google AI>
CORS_ORIGINS=["https://tudominio.com"]
```

> `CORS_ORIGINS` va **siempre** en formato JSON, incluso con un solo origen:
> `cors_origins` es `list[str]` y un string plano aborta el arranque con
> `SettingsError: error parsing value for field "cors_origins"`.

> Con `APP_ENV=production`, api y worker rechazan el arranque si alguna de estas
> variables conserva un valor por defecto o débil (`replace_me`, `postgres`,
> `minioadmin`, vacío), o si `CORS_ORIGINS` contiene `localhost`. Las validaciones
> comunes viven en `packages/rc7_shared_config`; la API añade las de `JWT_SECRET`,
> `BOOTSTRAP_ADMIN_PASSWORD` y `CORS_ORIGINS`.

---

## Paso 2 — Certificados TLS

Los certificados deben estar en `infra/nginx/ssl/` antes de iniciar el stack.

### Opción A: Let's Encrypt con Certbot (recomendado)

```bash
# Instalar certbot en el servidor
sudo apt install certbot -y

# Obtener certificado (el puerto 80 debe estar libre)
sudo certbot certonly --standalone -d tudominio.com

# Copiar certificados
mkdir -p infra/nginx/ssl
sudo cp /etc/letsencrypt/live/tudominio.com/fullchain.pem infra/nginx/ssl/
sudo cp /etc/letsencrypt/live/tudominio.com/privkey.pem   infra/nginx/ssl/
```

### Opción B: Certificado propio / corporativo

Copiar `fullchain.pem` y `privkey.pem` directamente en `infra/nginx/ssl/`.

---

## Paso 3 — Migrar datos del servidor origen

### 3a. Exportar en la máquina de origen

Con el stack de desarrollo corriendo:

```bash
bash scripts/export-data.sh
# Crea: migration_export_YYYYMMDD_HHMMSS/
#         ├── postgres_dump.sql
#         └── minio_data.tar.gz
```

### 3b. Transferir al servidor de producción

```bash
scp -r migration_export_TIMESTAMP/ user@SERVER:/ruta/al/proyecto/
```

### 3c. Importar en el servidor de producción

```bash
# Requiere que el .env de producción ya esté configurado
bash scripts/import-data.sh migration_export_TIMESTAMP
```

El script:
1. Arranca PostgreSQL y MinIO
2. Restaura el dump SQL en PostgreSQL
3. Copia los archivos de MinIO al named volume `minio_data`

---

## Paso 4 — Iniciar el stack de producción

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### Verificar estado

```bash
# Estado de todos los contenedores
docker compose -f docker-compose.prod.yml ps

# Logs en tiempo real
docker compose -f docker-compose.prod.yml logs -f

# Healthcheck de la API
curl -s https://tudominio.com/api/v1/health/ | python3 -m json.tool
```

---

## Comandos de mantenimiento

```bash
# Reconstruir y reiniciar tras un git pull
docker compose -f docker-compose.prod.yml up -d --build

# Ver logs de un servicio específico
docker compose -f docker-compose.prod.yml logs --tail=100 api

# Reiniciar un servicio sin reconstruir
docker compose -f docker-compose.prod.yml restart worker

# Detener todo
docker compose -f docker-compose.prod.yml down
```

---

## CI/CD con GitHub Actions

Ya está implementado en `.github/workflows/deploy.yml`, con tres jobs: `test-frontend`,
`test-backend` (api y worker) y `deploy`, que solo corre en push a `main` y si todos los
tests pasan.

```
git push a main → tests (web + api + worker) → SSH al servidor → git pull
                → docker compose -f docker-compose.prod.yml up -d --build --wait
                → rollback automático si algún healthcheck falla
```

Secrets necesarios en GitHub Actions:
- `SERVER_HOST` — IP o dominio del servidor
- `SERVER_USER` — Usuario SSH
- `SSH_PRIVATE_KEY` — Clave privada SSH
- `SERVER_WORKDIR` — Ruta absoluta del proyecto en el servidor

El `.env` **no** se despliega desde un secret: debe existir ya en el servidor con
`chmod 600` y el workflow aborta si falta. Es deliberado — evita la expansión
frágil de secretos multilínea y preserva los overrides propios de esa máquina. Se
instala una sola vez:

```bash
scp .env.example user@host:/ruta/del/proyecto/.env && chmod 600 .env   # y rellenarlo
```

```yaml
# .github/workflows/deploy.yml (esquema real)
- name: Deploy
  uses: appleboy/ssh-action@v1.2.0
  with:
    host: ${{ secrets.SERVER_HOST }}
    script: |
      cd "${{ secrets.SERVER_WORKDIR }}"
      [[ -f .env ]] || exit 1          # aborta si no existe; nunca lo escribe
      git pull origin main
      docker compose -f docker-compose.prod.yml up -d --build --wait
```

---

## Portabilidad AWS ↔ On-premises

El stack completo es portable entre entornos porque:
- PostgreSQL corre en contenedor (no depende de RDS ni de servicios cloud)
- MinIO es S3-compatible y corre en cualquier servidor
- `docker-compose.prod.yml` no referencia ningún servicio específico de AWS

Para migrar entre entornos (AWS → on-premises o viceversa), ejecutar el mismo flujo de `export-data.sh` / `import-data.sh`.
