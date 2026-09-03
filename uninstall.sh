#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
rm -rf "$APP_DIR/.venv"
find "$APP_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true

echo "已删除当前仓库的 .venv 与 Python 缓存"
echo "源码、配置和 output 数据未删除"
