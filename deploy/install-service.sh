#!/usr/bin/env bash
set -euo pipefail

sudo install -m 644 deploy/gateway-be.service /etc/systemd/system/gateway-be.service
sudo systemctl daemon-reload
sudo systemctl enable --now gateway-be.service
