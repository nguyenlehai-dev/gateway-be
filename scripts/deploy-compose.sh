#!/usr/bin/env bash

set -euo pipefail

ENVIRONMENT="${1:-}"

case "${ENVIRONMENT}" in
  staging|prod)
    ;;
  *)
    echo "Usage: $0 <staging|prod>"
    exit 1
    ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/deploy/${ENVIRONMENT}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing env file: ${ENV_FILE}"
  echo "Create it from deploy/${ENVIRONMENT}/.env.example first."
  exit 1
fi

docker compose --env-file "${ENV_FILE}" -f "${ROOT_DIR}/docker-compose.yml" -p "gateway-${ENVIRONMENT}" up -d --build
docker compose --env-file "${ENV_FILE}" -f "${ROOT_DIR}/docker-compose.yml" -p "gateway-${ENVIRONMENT}" ps

CONTAINER_NAME="gateway-${ENVIRONMENT}-gateway-be-1"
if docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  docker exec "${CONTAINER_NAME}" alembic upgrade head >/dev/null 2>&1 || true
  docker exec "${CONTAINER_NAME}" python scripts/seed_phase2.py >/dev/null 2>&1 || true
  docker exec "${CONTAINER_NAME}" python scripts/seed_auth.py >/dev/null 2>&1 || true
fi
