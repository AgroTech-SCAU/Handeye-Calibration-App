#!/usr/bin/env bash
set -eo pipefail
export PYTHONNOUSERSITE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${HANDEYE_CORE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
RUNTIME_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/handeye-calibration"
VENV="$RUNTIME_DIR/.venv"

find_ros_setup() {
  if [ -n "${ROS_SETUP:-}" ] && [ -f "$ROS_SETUP" ]; then
    printf '%s\n' "$ROS_SETUP"
    return
  fi
  if [ -n "${ROS_DISTRO:-}" ] && [ -f "/opt/ros/$ROS_DISTRO/setup.bash" ]; then
    printf '%s\n' "/opt/ros/$ROS_DISTRO/setup.bash"
    return
  fi
  local version candidate
  version="$(. /etc/os-release 2>/dev/null; printf '%s' "${VERSION_ID:-}")"
  case "$version" in
    20.04) candidate=/opt/ros/foxy/setup.bash ;;
    22.04) candidate=/opt/ros/humble/setup.bash ;;
    24.04) candidate=/opt/ros/jazzy/setup.bash ;;
    *) candidate= ;;
  esac
  if [ -n "$candidate" ] && [ -f "$candidate" ]; then
    printf '%s\n' "$candidate"
    return
  fi
  local found=()
  shopt -s nullglob
  found=(/opt/ros/*/setup.bash)
  shopt -u nullglob
  if [ "${#found[@]}" -eq 1 ]; then
    printf '%s\n' "${found[0]}"
  fi
}

ROS_FILE="$(find_ros_setup || true)"
if [ -n "$ROS_FILE" ]; then
  echo "[HandEye] ROS setup: $ROS_FILE"
  # ROS setup scripts may reference unset variables, so do not enable nounset
  # shellcheck disable=SC1090
  source "$ROS_FILE"
else
  echo "[HandEye] ROS2 setup not detected; manual calibration remains available."
fi

if [ -n "${HANDEYE_SYSTEM_PYTHON:-}" ]; then
  PYTHON_BIN="$HANDEYE_SYSTEM_PYTHON"
elif [ -x /usr/bin/python3 ]; then
  # ROS2 apt packages are compiled for the distro system Python. Prefer it over
  # conda/pyenv shims in PATH to keep rclpy ABI-compatible
  PYTHON_BIN=/usr/bin/python3
else
  PYTHON_BIN="$(command -v python3 || true)"
fi
if [ -z "$PYTHON_BIN" ]; then
  echo "[HandEye] python3 not found" >&2
  exit 1
fi

mkdir -p "$RUNTIME_DIR"
if [ ! -x "$VENV/bin/python" ]; then
  echo "[HandEye] Creating runtime venv with $PYTHON_BIN"
  if ! "$PYTHON_BIN" -m venv --system-site-packages "$VENV"; then
    echo "[HandEye] failed to create venv. Install python3-venv for your Ubuntu release." >&2
    exit 1
  fi
fi

"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install --prefer-binary -r "$APP_DIR/requirements.txt"

"$VENV/bin/python" - <<'PY'
import cv2
import numpy
import scipy
import yaml
print(f"[HandEye] Python runtime OK: numpy={numpy.__version__}, opencv={cv2.__version__}, scipy={scipy.__version__}")
PY

if [ -n "$ROS_FILE" ]; then
  "$VENV/bin/python" - <<'PY'
import rclpy
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, String
print("[HandEye] ROS2 Python imports OK")
PY
fi

echo "[HandEye] Runtime installed: $VENV"
