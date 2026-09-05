#!/usr/bin/env bash
set -e
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$APP_DIR/launch.sh" "$@"
