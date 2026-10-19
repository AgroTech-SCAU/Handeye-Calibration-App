#!/usr/bin/env sh
set -eu

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$repo_root" ]; then
  echo "[AgroTech] 当前目录不在 Git 仓库中"
  exit 1
fi

cd "$repo_root"
git config --local core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/pre-push 2>/dev/null || true

echo "[AgroTech] 已启用本仓库的本地 Git 防误操作提醒"
echo "[AgroTech] core.hooksPath = $(git config --local --get core.hooksPath)"
echo "[AgroTech] 注意：Hook 只是本地体验增强，main 的最终保护仍由 GitHub Ruleset 提供"
