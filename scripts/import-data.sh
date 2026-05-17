#!/usr/bin/env bash
# Restore all persistent data on the new server after migration.
#
# What it restores:
#   - PostgreSQL dump into the running postgres container
#   - MinIO files into the minio_data named Docker volume
#
# Usage (from project root on the NEW server):
#   bash scripts/import-data.sh <export_dir>
#
# Example:
#   bash scripts/import-data.sh migration_export_20260517_143000
#
# Prerequisites:
#   - .env file with production values already in place
#   - The export directory transferred from the source machine
#   - Docker and Docker Compose installed

set -euo pipefail

IMPORT_DIR="${1:?Usage: $0 <export_dir>}"

if [[ ! -d "${IMPORT_DIR}" ]]; then
  echo "Error: directory '${IMPORT_DIR}' not found." >&2
  exit 1
fi

# ─── Load env vars ────────────────────────────────────────────────────────────
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-rc7_assistant}"

echo "╔══════════════════════════════════════════════════════╗"
echo "║          RC7 — Data Import (Migration Restore)       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Import source    : ${IMPORT_DIR}"
echo "PostgreSQL DB    : ${POSTGRES_DB} (user: ${POSTGRES_USER})"
echo ""

# ─── Create required directories ─────────────────────────────────────────────
mkdir -p infra/nginx/ssl

# ─── Start only infrastructure services ──────────────────────────────────────
echo "▶ Starting infrastructure (postgres, redis, minio)..."
docker compose -f docker-compose.prod.yml up -d postgres redis minio

echo "  Waiting for postgres to be ready..."
until docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" > /dev/null 2>&1; do
  printf "."
  sleep 2
done
echo ""
echo "  ✓ PostgreSQL is ready"

# ─── Restore PostgreSQL dump ──────────────────────────────────────────────────
DUMP_FILE="${IMPORT_DIR}/postgres_dump.sql"
if [[ -f "${DUMP_FILE}" && -s "${DUMP_FILE}" ]]; then
  echo "▶ Restoring PostgreSQL from ${DUMP_FILE}..."
  docker compose -f docker-compose.prod.yml exec -T postgres \
    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
    < "${DUMP_FILE}"
  echo "  ✓ PostgreSQL restored"
else
  echo "  ⚠ ${DUMP_FILE} not found or empty — skipping PostgreSQL restore"
fi

# ─── Restore MinIO data into the named volume ─────────────────────────────────
MINIO_ARCHIVE="${IMPORT_DIR}/minio_data.tar.gz"
if [[ -f "${MINIO_ARCHIVE}" && -s "${MINIO_ARCHIVE}" ]]; then
  echo "▶ Restoring MinIO data into minio_data volume..."

  # Resolve the actual Docker volume name (prefixed by the Compose project name)
  COMPOSE_PROJECT=$(docker compose -f docker-compose.prod.yml config --format json \
    2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" \
    2>/dev/null || basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]_-')

  VOLUME_NAME="${COMPOSE_PROJECT}_minio_data"

  # Use a temporary Alpine container to unpack the archive into the volume
  docker run --rm \
    -v "$(pwd)/${MINIO_ARCHIVE}:/backup.tar.gz:ro" \
    -v "${VOLUME_NAME}:/data" \
    alpine:latest \
    sh -c "tar -xzf /backup.tar.gz -C /data"

  echo "  ✓ MinIO data restored into volume '${VOLUME_NAME}'"
else
  echo "  ⚠ ${MINIO_ARCHIVE} not found or empty — skipping MinIO restore"
fi

echo ""
echo "✓ Import complete."
echo ""
echo "Next steps:"
echo "  1. Ensure infra/nginx/ssl/fullchain.pem and privkey.pem are in place"
echo "  2. Start the full stack:"
echo "       docker compose -f docker-compose.prod.yml up -d --build"
echo "  3. Check all services are healthy:"
echo "       docker compose -f docker-compose.prod.yml ps"
