#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

python3 scripts/verify_core.py
npm test

BUILDER="$APP_DIR/node_modules/.bin/electron-builder"
[ -x "$BUILDER" ] || { echo "[HandEye] electron-builder not found; run ./install.sh first" >&2; exit 1; }

if ! "$BUILDER" --linux AppImage deb --x64; then
  echo "[HandEye] release download failed, retry via npmmirror" >&2
  ELECTRON_MIRROR="${ELECTRON_MIRROR:-https://npmmirror.com/mirrors/electron/}" \
  ELECTRON_BUILDER_BINARIES_MIRROR="${ELECTRON_BUILDER_BINARIES_MIRROR:-https://npmmirror.com/mirrors/electron-builder-binaries/}" \
  "$BUILDER" --linux AppImage deb --x64
fi

printf '\nArtifacts:\n'
find dist -maxdepth 1 -type f \( -name '*.AppImage' -o -name '*.deb' \) -print
