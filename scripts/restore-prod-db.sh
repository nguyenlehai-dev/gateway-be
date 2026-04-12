#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: $0 /absolute/path/to/backup/gateway-prod.db"
  exit 1
fi

SOURCE_DB="$1"
DB_PATH="${DB_PATH:-/home/vpsroot/apps/gateway-prod/be/deploy/prod/gateway-prod.db}"
PROJECT_DIR="${PROJECT_DIR:-/home/vpsroot/apps/gateway-prod/be}"
ENV_FILE="${ENV_FILE:-/home/vpsroot/apps/gateway-prod/be/deploy/prod/.env}"
BACKUP_DIR="${BACKUP_DIR:-/home/vpsroot/backups/gateway-prod}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SAFETY_DIR="${BACKUP_DIR}/pre-restore-${STAMP}"

if [ ! -f "${SOURCE_DB}" ]; then
  echo "Backup file not found: ${SOURCE_DB}"
  exit 1
fi

mkdir -p "${SAFETY_DIR}"

python3 - <<PY
import os
import sqlite3
src = sqlite3.connect(r"${DB_PATH}")
dst = sqlite3.connect(r"${SAFETY_DIR}/gateway-prod.db")
with dst:
    src.backup(dst)
src.close()
dst.close()
PY

cp -f "${ENV_FILE}" "${SAFETY_DIR}/.env"

docker compose -p gateway-prod -f "${PROJECT_DIR}/docker-compose.yml" --env-file "${ENV_FILE}" stop gateway-be gateway-job-worker

cp -f "${SOURCE_DB}" "${DB_PATH}"
rm -f "${DB_PATH}-wal" "${DB_PATH}-shm"

docker compose -p gateway-prod -f "${PROJECT_DIR}/docker-compose.yml" --env-file "${ENV_FILE}" up -d gateway-be gateway-job-worker

echo "Restore completed."
echo "Safety backup saved at ${SAFETY_DIR}"
