#!/usr/bin/env bash
set -eo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"
export PYTHONNOUSERSITE=1

if [ -x /usr/bin/python3 ]; then
  PYTHON_BIN=/usr/bin/python3
else
  PYTHON_BIN="$(command -v python3 || true)"
fi
[ -n "$PYTHON_BIN" ] || { echo "[HandEye] python3 not found"; exit 1; }
command -v node >/dev/null || { echo "[HandEye] Node.js not found, recommend Node 20 or 22 LTS"; exit 1; }
command -v npm >/dev/null || { echo "[HandEye] npm not found"; exit 1; }
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
if [ "$NODE_MAJOR" -lt 20 ]; then
  echo "[HandEye] Node.js 20+ required for the source build, found $(node --version)" >&2
  exit 1
fi

run_with_heartbeat() {
  local label="$1"
  local limit="$2"
  shift 2
  local log_file
  log_file="$(mktemp)"
  local start_time
  start_time="$(date +%s)"

  echo "[HandEye] $label"
  set +e
  "$@" >"$log_file" 2>&1 &
  local pid=$!
  set -e
  trap 'echo "[HandEye] install interrupted" >&2; kill "$pid" 2>/dev/null || true; sleep 1; kill -9 "$pid" 2>/dev/null || true; exit 130' INT TERM

  while kill -0 "$pid" 2>/dev/null; do
    sleep 1
    local now elapsed
    now="$(date +%s)"
    elapsed=$((now - start_time))
    if [ "$elapsed" -gt 0 ] && [ $((elapsed % 5)) -eq 0 ]; then
      echo "[HandEye] $label, ${elapsed}s"
    fi
    if [ "$elapsed" -ge "$limit" ]; then
      echo "[HandEye] $label timed out after ${limit}s" >&2
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      cat "$log_file" >&2
      rm -f "$log_file"
      return 124
    fi
  done

  set +e
  wait "$pid"
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    cat "$log_file" >&2
  fi
  rm -f "$log_file"
  trap - INT TERM
  return "$rc"
}

if [ ! -d .venv ]; then
  echo "[HandEye] creating Python environment"
  if ! "$PYTHON_BIN" -m venv --system-site-packages .venv; then
    echo "[HandEye] failed to create .venv, install python3-venv" >&2
    exit 1
  fi
fi

echo "[HandEye] installing Python dependencies"
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python scripts/verify_core.py

echo "[HandEye] checking Python backend"
HANDEYE_MOCK=1 HANDEYE_DATA_DIR="$APP_DIR/.install-smoke" \
  ./.venv/bin/python scripts/smoke_backend.py
rm -rf "$APP_DIR/.install-smoke"

echo "[HandEye] installing Node packages"
run_with_heartbeat "Node package install" 300 \
  npm install --ignore-scripts --no-audit --no-fund --progress=false --loglevel=error

ELECTRON_BIN="$APP_DIR/node_modules/electron/dist/electron"
if [ ! -x "$ELECTRON_BIN" ]; then
  ELECTRON_INSTALL="$APP_DIR/node_modules/electron/install.js"
  [ -f "$ELECTRON_INSTALL" ] || { echo "[HandEye] Electron installer missing after npm install" >&2; exit 1; }

  MIRROR="${ELECTRON_MIRROR:-https://npmmirror.com/mirrors/electron/}"
  if ! run_with_heartbeat "Electron binary download via mirror" 420 \
    env ELECTRON_MIRROR="$MIRROR" npm_config_electron_mirror="$MIRROR" \
    node "$ELECTRON_INSTALL"; then
    echo "[HandEye] mirror download failed, retry official Electron source" >&2
    rm -rf "$APP_DIR/node_modules/electron/dist" "$APP_DIR/node_modules/electron/path.txt" 2>/dev/null || true
    run_with_heartbeat "Electron binary download via official source" 420 \
      env -u ELECTRON_MIRROR -u npm_config_electron_mirror \
      node "$ELECTRON_INSTALL"
  fi
else
  echo "[HandEye] Electron binary already present"
fi

[ -x "$ELECTRON_BIN" ] || { echo "[HandEye] Electron binary install failed" >&2; exit 1; }
npm run verify:static

echo ""
echo "[HandEye] install complete"
echo "  Python: $APP_DIR/.venv/bin/python"
echo "  Electron: $ELECTRON_BIN"
echo "  Start: ./launch.sh"
