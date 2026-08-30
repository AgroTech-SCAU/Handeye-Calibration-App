@echo off
setlocal
cd /d "%~dp0"
python -m pip install pyinstaller -r requirements.txt
python -m PyInstaller --noconfirm --clean --windowed --name HandEyeCalibration --add-data "algorithms;algorithms" --add-data "assets;assets" --hidden-import scipy.optimize --hidden-import rclpy --hidden-import geometry_msgs.msg --hidden-import sensor_msgs.msg --hidden-import std_msgs.msg app.py
echo Build output: dist\HandEyeCalibration\
echo Note: start the EXE from a configured ROS2 terminal for automatic mode.
pause
