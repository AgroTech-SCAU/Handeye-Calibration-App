#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"
python3 -m pip install pyinstaller -r requirements.txt
python3 -m PyInstaller --noconfirm --clean --windowed --name HandEyeCalibration --add-data "algorithms:algorithms" --add-data "assets:assets" --hidden-import scipy.optimize --hidden-import rclpy --hidden-import geometry_msgs.msg --hidden-import sensor_msgs.msg --hidden-import std_msgs.msg app.py
echo "Build output: dist/HandEyeCalibration/"
echo "Start it after sourcing ROS2 when using automatic mode."
