#!/usr/bin/env bash
# Export all persistent data for migration to a new server.
#
# What it exports:
#   - PostgreSQL full dump (schema + data, including pgvector embeddings)
#   - MinIO files (PDFs and manuals stored in ./storage/data)
#
# Redis is intentionally skipped: it holds only session data (JWT tokens,
# cache) that expires naturally. Users will need to log in again on the
# new server, which is acceptable.
#
# Usage (from project root):
#   bash scripts/export-data.sh
#
# Output:
#   migration_export_YYYYMMDD_HHMMSS/
#     postgres_dump.sql
#     minio_data.tar.gz
#     README.txt

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EXPORT_DIR="migration_export_${TIMESTAMP}"

# ─── Load env vars so we can reference DB credentials ────────────────────────
if [[ -f .env ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip blank lines and comments
    [[ -z "${line//[[:space:]]/}" || "$line" == \#* ]] && continue
    export "$line"
  done < .env
fi

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-rc7_assistant}"

echo "╔══════════════════════════════════════════════════════╗"
echo "║          RC7 — Data Export for Migration             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Export directory : ${EXPORT_DIR}"
echo "PostgreSQL DB    : ${POSTGRES_DB} (user: ${POSTGRES_USER})"
echo "MinIO source     : ./storage/data"
echo ""

mkdir -p "${EXPORT_DIR}"

# ─── PostgreSQL dump ─────────────────────────────────────────────────────────
echo "▶ Exporting PostgreSQL..."
docker compose exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
  > "${EXPORT_DIR}/postgres_dump.sql"
DUMP_SIZE=$(du -sh "${EXPORT_DIR}/postgres_dump.sql" | cut -f1)
echo "  ✓ postgres_dump.sql (${DUMP_SIZE})"

# ─── MinIO files ─────────────────────────────────────────────────────────────
echo "▶ Archiving MinIO data..."
if [[ -d "storage/data" && -n "$(ls -A storage/data 2>/dev/null)" ]]; then
  tar -czf "${EXPORT_DIR}/minio_data.tar.gz" -C storage/data .
  MINIO_SIZE=$(du -sh "${EXPORT_DIR}/minio_data.tar.gz" | cut -f1)
  echo "  ✓ minio_data.tar.gz (${MINIO_SIZE})"
else
  echo "  ⚠ storage/data is empty — skipping MinIO archive"
  touch "${EXPORT_DIR}/minio_data.tar.gz"
fi

# ─── README ──────────────────────────────────────────────────────────────────
cat > "${EXPORT_DIR}/README.txt" << EOF
RC7 Migration Export — ${TIMESTAMP}
=====================================
PostgreSQL : postgres_dump.sql  (${DUMP_SIZE:-0})
MinIO      : minio_data.tar.gz

To restore on the new server, run:
  bash scripts/import-data.sh ${EXPORT_DIR}
EOF

echo ""
echo "✓ Export complete: ${EXPORT_DIR}/"
echo ""
echo "Next steps:"
echo "  1. Transfer the export directory to the server:"
echo "       scp -r ${EXPORT_DIR}/ user@SERVER_IP:/path/to/rc7_programming_assistant/"
echo "  2. On the server, run:"
echo "       bash scripts/import-data.sh ${EXPORT_DIR}"
