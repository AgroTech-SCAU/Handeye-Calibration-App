# HandEye Calibration 使用指南

## 1 启动

源码模式

```bash
./install.sh
./launch.sh
```

安装脚本会单独下载 Electron 二进制，并在等待期间持续显示进度

Electron 二进制优先使用 `npmmirror`，镜像不可用时自动回退到官方源

可以手动指定 Electron 镜像

```bash
ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/ ./install.sh
```

Release 模式可以直接启动 AppImage，或从系统应用菜单启动 deb 安装后的 HandEye Calibration

## 2 Connect

先选择输出目录，再配置相机与机器人输入

本地相机模式使用 OpenCV camera index 和分辨率

ROS2 自动采样可以选择 `PoseStamped` 或 `JointState`

`PoseStamped` 输入填写机械臂末端位姿话题，例如 `/arm/pose`

`JointState` 输入填写关节状态话题，并确认 `algorithms/robot_params.yaml` 与机械臂参数一致

完成参数后连接 ROS2，并确认 Camera 和 ROS2 状态正常

## 3 Camera Intrinsics

设置棋盘内角点数量和方格尺寸 mm

采集时让棋盘覆盖画面中心、四角、不同距离和不同倾角

正式标定建议使用 Standard 模式，并采集足够数量且分布充分的图像

完成采集后执行 Solve & Save

输出文件

```text
camera_intrinsics.yaml
```

## 4 Hand-Eye Sampling

标定过程中保持棋盘固定

每次采样按以下顺序操作

1. 移动机械臂到新的位置与姿态
2. 尽量改变不同旋转轴的激励
3. 等待机械臂停稳
4. 确认棋盘完整可见
5. 点击 Capture Sample

完成采样后保存数据

```text
samples.yaml
```

## 5 Solve And Verify

推荐工作流

```text
Diagnose -> Solve -> Verify
```

Robust 适合作为常规求解入口

OpenCV 可用于直接方法对照

Bundle Adjustment 可用于带完整角点数据的重投影精化

结果保存在输出目录

```text
camera_intrinsics.yaml
samples.yaml
samples_result.yaml
```

## 6 ROS2 Environment

源码启动可以显式指定 ROS2 setup

```bash
ROS_SETUP=/opt/ros/humble/setup.bash ./launch.sh
```

Ubuntu 与 ROS2 的默认映射

```text
20.04 -> Foxy
22.04 -> Humble
24.04 -> Jazzy
```

没有 ROS2 时仍可以使用手动机器人数据输入

## 7 Runtime

Release 应用需要 Python 标定运行环境

Settings 页面可以执行 Install Runtime

运行环境位于用户目录

```text
~/.local/share/handeye-calibration/.venv/
```

该目录不需要 sudo

## 8 Language

Settings 页面可以在简体中文和 English 之间切换

首次启动根据系统语言自动选择，后续使用用户最后一次选择的语言

切换语言不会重启 backend，也不会清空当前 ROS2 连接和采样状态

## 9 Build Release

```bash
./install.sh
./build_linux.sh
```

如果 electron-builder 下载依赖失败，构建脚本会自动使用 `npmmirror` 重试

构建产物位于

```text
dist/
```

目标格式

```text
AppImage
deb
```
