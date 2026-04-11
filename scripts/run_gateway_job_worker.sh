#!/usr/bin/env bash

set -euo pipefail

INTERVAL_SECONDS="${GATEWAY_JOB_RUNNER_INTERVAL_SECONDS:-5}"

while true; do
  python -m app.scripts.process_gateway_jobs
  sleep "${INTERVAL_SECONDS}"
done
