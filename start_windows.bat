@echo off
setlocal
cd /d "%~dp0"

if defined ROS_SETUP (
  call "%ROS_SETUP%"
) else if exist "C:\dev\ros2_humble\local_setup.bat" (
  call "C:\dev\ros2_humble\local_setup.bat"
)

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found in PATH.
  pause
  exit /b 1
)

python app.py
if errorlevel 1 pause
