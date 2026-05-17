#!/usr/bin/env bash
# Backup PostgreSQL and MinIO data to a timestamped directory.
#
# Creates:
#   backups/YYYY-MM-DD_HH-MM-SS/postgres.sql.gz   — compressed pg_dump
#   backups/YYYY-MM-DD_HH-MM-SS/minio.tar.gz      — MinIO bucket archive
#
# Intended to run from cron on the host, e.g.:
#   0 2 * * * cd /srv/rc7 && bash scripts/backup.sh >> logs/backup.log 2>&1
#
# Retention: keeps the 7 most recent backup directories (configurable via
# BACKUP_KEEP_DAYS below).
#
# Usage (from project root):
#   bash scripts/backup.sh
#
# Prerequisites:
#   - .env file with production values in the project root
#   - docker-compose.prod.yml stack running (override with COMPOSE_FILE env var)
#   - Docker available to the user running this script

set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────────────
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_ROOT="$(pwd)/backups"
TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

# ─── Load env vars ────────────────────────────────────────────────────────────
if [[ -f .env ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip blank lines and comments
    [[ -z "${line//[[:space:]]/}" || "$line" == \#* ]] && continue
    export "$line"
  done < .env
fi

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-rc7_assistant}"

# ─── Helpers ──────────────────────────────────────────────────────────────────
log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

# ─── Preflight checks ─────────────────────────────────────────────────────────
command -v docker > /dev/null 2>&1 || die "docker not found"

# Verify the postgres container is running
docker compose -f "${COMPOSE_FILE}" ps postgres \
  | grep -qE "(Up|running)" || die "postgres container is not running"

# ─── Create backup directory ──────────────────────────────────────────────────
mkdir -p "${BACKUP_DIR}"
log "Backup directory: ${BACKUP_DIR}"

# ─── PostgreSQL dump ──────────────────────────────────────────────────────────
log "▶ Dumping PostgreSQL database '${POSTGRES_DB}'..."

docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --no-password \
  | gzip > "${BACKUP_DIR}/postgres.sql.gz"

POSTGRES_SIZE=$(du -sh "${BACKUP_DIR}/postgres.sql.gz" | cut -f1)
log "  PostgreSQL dump: ${POSTGRES_SIZE} — OK"

# ─── MinIO backup ─────────────────────────────────────────────────────────────
log "▶ Archiving MinIO data volume..."

# Use a temporary Alpine container that mounts the named volume read-only
docker run --rm \
  --volumes-from "$(docker compose -f "${COMPOSE_FILE}" ps -q minio)" \
  -v "${BACKUP_DIR}:/backup" \
  alpine:3.19 \
  tar -czf /backup/minio.tar.gz -C /data .

MINIO_SIZE=$(du -sh "${BACKUP_DIR}/minio.tar.gz" | cut -f1)
log "  MinIO archive: ${MINIO_SIZE} — OK"

# ─── Retention — remove backups older than BACKUP_KEEP_DAYS ──────────────────
log "▶ Applying retention policy (keep last ${BACKUP_KEEP_DAYS} days)..."

_total=$(find "${BACKUP_ROOT}" -maxdepth 1 -type d -name "????-??-??_??-??-??" | wc -l | tr -d ' ')
_to_remove=$(( _total - BACKUP_KEEP_DAYS ))

if [[ "${_to_remove}" -gt 0 ]]; then
  find "${BACKUP_ROOT}" -maxdepth 1 -type d \
    -name "????-??-??_??-??-??" \
    | sort \
    | head -n "${_to_remove}" \
    | while read -r old_dir; do
        log "  Removing old backup: $(basename "${old_dir}")"
        rm -rf "${old_dir}"
      done
else
  log "  Nothing to remove (${_total} backup(s) found, keeping up to ${BACKUP_KEEP_DAYS})"
fi

# ─── Summary ──────────────────────────────────────────────────────────────────
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
log "══════════════════════════════════════════════"
log "Backup complete: ${TIMESTAMP} (${TOTAL_SIZE} total)"
log "  postgres.sql.gz : ${POSTGRES_SIZE}"
log "  minio.tar.gz    : ${MINIO_SIZE}"
log "══════════════════════════════════════════════"
