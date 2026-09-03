#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

if ! python3 -c 'import tkinter' >/dev/null 2>&1; then
  echo "缺少 Tk；请先安装当前 Linux 发行版对应的 Python Tk 包" >&2
  exit 1
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "当前 Python 缺少 venv 模块，请先安装对应的 python3-venv 包" >&2
  exit 1
fi

# 始终重建仓库本地虚拟环境，避免继承旧环境中的 NumPy/OpenCV ABI 冲突
rm -rf "$VENV_DIR"
python3 -m venv "$APP_DIR/.venv"
# pip 安装阶段不继承当前 ROS/用户 shell 的 Python 路径，避免把宿主 ROS 包
# 误判为本 venv 已安装依赖，或产生无关的依赖解析告警
env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 \
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 \
  "$VENV_DIR/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

chmod +x "$APP_DIR/launch.sh" "$APP_DIR/start_ubuntu.sh" "$APP_DIR/uninstall.sh"

echo "环境初始化完成: $VENV_DIR"
echo "启动: ./launch.sh"
echo "如果终端尚未 source ROS2，launch.sh 会尝试自动发现 /opt/ros 下唯一的发行版"
