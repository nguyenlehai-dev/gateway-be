#!/usr/bin/env bash

set -euo pipefail

TARGET="${1:-}"

case "${TARGET}" in
  staging)
    APP_URL="http://127.0.0.1:8082"
    PUBLIC_URL="https://testgateway.plxeditor.com"
    ;;
  prod)
    APP_URL="http://127.0.0.1:8081"
    PUBLIC_URL="https://gateway.plxeditor.com"
    ;;
  *)
    echo "Usage: $0 <staging|prod>"
    exit 1
    ;;
esac

echo "[verify] Internal health"
curl -fsS "${APP_URL}/up"
echo

echo "[verify] Public root"
curl -fsSI "${PUBLIC_URL}/"
echo

echo "[verify] Public API"
curl -fsS "${PUBLIC_URL}/api/v1/vendors?limit=1"
echo
