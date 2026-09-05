#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"
rm -rf .venv node_modules .runtime dist renderer-smoke.png
echo "[HandEye] source runtime removed from repository only."
echo "Per-user Release runtime, if present, is intentionally kept at ~/.local/share/handeye-calibration/.venv"
