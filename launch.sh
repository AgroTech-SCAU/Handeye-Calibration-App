#!/usr/bin/env bash
set -eo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"
export PYTHONNOUSERSITE=1

if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
  echo "[HandEye] .venv not found. Run ./install.sh first."
  exit 1
fi
if [ ! -x "$APP_DIR/node_modules/.bin/electron" ]; then
  echo "[HandEye] Electron dependency not found. Run ./install.sh first."
  exit 1
fi

# Do not enable nounset before sourcing ROS; several ROS setup scripts read unset variables
if [ -n "${ROS_SETUP:-}" ] && [ -f "$ROS_SETUP" ]; then
  # shellcheck disable=SC1090
  source "$ROS_SETUP"
elif [ -z "${ROS_DISTRO:-}" ]; then
  VERSION_ID="$(. /etc/os-release 2>/dev/null; printf '%s' "${VERSION_ID:-}")"
  case "$VERSION_ID" in
    20.04) CANDIDATE=/opt/ros/foxy/setup.bash ;;
    22.04) CANDIDATE=/opt/ros/humble/setup.bash ;;
    24.04) CANDIDATE=/opt/ros/jazzy/setup.bash ;;
    *) CANDIDATE= ;;
  esac
  if [ -n "$CANDIDATE" ] && [ -f "$CANDIDATE" ]; then
    # shellcheck disable=SC1090
    source "$CANDIDATE"
  fi
fi
set -u

export HANDEYE_PYTHON="$APP_DIR/.venv/bin/python"
export HANDEYE_DATA_DIR="${HANDEYE_DATA_DIR:-$APP_DIR/.runtime}"
mkdir -p "$HANDEYE_DATA_DIR"

echo "[HandEye] Electron GUI"
echo "[HandEye] Python: $HANDEYE_PYTHON"
echo "[HandEye] ROS2: ${ROS_DISTRO:-not sourced (manual mode still available)}"
exec "$APP_DIR/node_modules/.bin/electron" "$APP_DIR"
