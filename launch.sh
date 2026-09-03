#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${APP_DIR}/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "未找到仓库本地 .venv，请先运行: ./install.sh" >&2
  exit 1
fi

have_rclpy() {
  PYTHONNOUSERSITE=1 "$VENV_PYTHON" - <<'PY' >/dev/null 2>&1
import rclpy
PY
}

source_ros_if_needed() {
  if have_rclpy; then
    return 0
  fi

  if [[ -n "${ROS_DISTRO:-}" && -f "/opt/ros/${ROS_DISTRO}/setup.bash" ]]; then
    # ROS setup 脚本本身不保证在 bash nounset 模式下可执行
    set +u
    # shellcheck disable=SC1090
    source "/opt/ros/${ROS_DISTRO}/setup.bash"
    set -u
    return 0
  fi

  shopt -s nullglob
  local setups=(/opt/ros/*/setup.bash)
  shopt -u nullglob
  if [[ ${#setups[@]} -eq 1 ]]; then
    set +u
    # shellcheck disable=SC1090
    source "${setups[0]}"
    set -u
    return 0
  fi

  cat >&2 <<'MSG'
HandEye Calibration 未找到唯一可用的 ROS2 Python 环境
请先 source 你要使用的 ROS2，例如：

  source /opt/ros/<distro>/setup.bash
  ./launch.sh

如果 /opt/ros 下同时存在多个 ROS2 发行版，也可以先设置 ROS_DISTRO
MSG
  return 1
}

source_ros_if_needed

if ! have_rclpy; then
  cat >&2 <<'MSG'
已加载 ROS2 环境，但当前仓库 .venv 仍无法 import rclpy
请确认创建 .venv 使用的 Python 主版本与该 ROS2 发行版提供的 Python ABI 一致
MSG
  exit 1
fi

PYTHONNOUSERSITE=1 exec "$VENV_PYTHON" "${APP_DIR}/app.py" "$@"
