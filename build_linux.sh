#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd -- "$(dirname -- "\${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

fail() {
  printf '[HandEye] Error: %s\n' "$*" >&2
  exit 1
}

[ "$(uname -s)" = "Linux" ] || fail "Linux is required to build AppImage and deb"
[ "$(uname -m)" = "x86_64" ] || fail "This build targets Linux x86_64 only"
command -v node >/dev/null 2>&1 || fail "Node.js not found, run ./install.sh first"
command -v npm >/dev/null 2>&1 || fail "npm not found, run ./install.sh first"

BUILDER="$APP_DIR/node_modules/.bin/electron-builder"
[ -x "$BUILDER" ] || fail "electron-builder not found, run ./install.sh first"

# Reject incomplete metadata and missing bundled files before packaging
node <<'NODE'
const fs = require('node:fs')
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'))
const email = typeof pkg.author === 'object' && pkg.author !== null
  ? pkg.author.email
  : typeof pkg.author === 'string'
    ? pkg.author.match(/<([^>]+)>/)?.[1]
    : undefined

if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
  console.error('[HandEye] Error: package.json author.email is required for deb packaging')
  process.exit(1)
}

const required = ['desktop/main.js', 'src/renderer/index.html', 'resources/icon.png']
for (const item of pkg.build?.extraResources ?? []) {
  if (typeof item.from === 'string') required.push(item.from)
}
const missing = required.filter(file => !fs.existsSync(file))
if (missing.length) {
  console.error('[HandEye] Error: required build files are missing: ' + missing.join(', '))
  process.exit(1)
}
NODE

OUTPUT_DIR="$APP_DIR/dist"
mkdir -p "$OUTPUT_DIR"
STAGING_DIR="$(mktemp -d "$OUTPUT_DIR/.build-linux.XXXXXX")"
cleanup() {
  if [ -n "\${STAGING_DIR:-}" ] && [ -d "$STAGING_DIR" ]; then
    rm -rf -- "$STAGING_DIR"
  fi
}
trap cleanup EXIT

printf '[HandEye] Building Linux AppImage and deb\n'
"$BUILDER" --linux AppImage deb --x64 --publish never \
  "-c.directories.output=$STAGING_DIR"

APPIMAGE_NAME="HandEye-Calibration-linux-x86_64.AppImage"
DEB_NAME="HandEye-Calibration-linux-amd64.deb"
STAGED_APPIMAGE="$STAGING_DIR/$APPIMAGE_NAME"
STAGED_DEB="$STAGING_DIR/$DEB_NAME"

[ -s "$STAGED_APPIMAGE" ] || fail "AppImage missing or empty after build"
[ -s "$STAGED_DEB" ] || fail "deb missing or empty after build"

# Validate Debian metadata when Debian packaging utilities are installed
if command -v dpkg-deb >/dev/null 2>&1; then
  dpkg-deb --field "$STAGED_DEB" >/dev/null || fail "Invalid deb package metadata"
fi

# Replace release assets only after both packages are produced successfully
mv -f -- "$STAGED_APPIMAGE" "$OUTPUT_DIR/$APPIMAGE_NAME"
mv -f -- "$STAGED_DEB" "$OUTPUT_DIR/$DEB_NAME"

printf '\n[HandEye] Build completed\n'
ls -lh -- "$OUTPUT_DIR/$APPIMAGE_NAME" "$OUTPUT_DIR/$DEB_NAME"
if command -v sha256sum >/dev/null 2>&1; then
  printf '\nSHA256:\n'
  sha256sum -- "$OUTPUT_DIR/$APPIMAGE_NAME" "$OUTPUT_DIR/$DEB_NAME"
fi
printf '\n[HandEye] Verify both packages before uploading them to GitHub Releases\n