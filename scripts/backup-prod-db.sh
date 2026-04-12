#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/home/vpsroot/backups/gateway-prod}"
DB_PATH="${DB_PATH:-/home/vpsroot/apps/gateway-prod/be/deploy/prod/gateway-prod.db}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET_DIR="${BACKUP_DIR}/${STAMP}"
TARGET_DB="${TARGET_DIR}/gateway-prod.db"

mkdir -p "${TARGET_DIR}"

python3 - <<PY
import sqlite3
source = sqlite3.connect(r"${DB_PATH}")
target = sqlite3.connect(r"${TARGET_DB}")
with target:
    source.backup(target)
source.close()
target.close()
PY

cp -f /home/vpsroot/apps/gateway-prod/be/deploy/prod/.env "${TARGET_DIR}/.env"
echo "Backup created at ${TARGET_DIR}"
