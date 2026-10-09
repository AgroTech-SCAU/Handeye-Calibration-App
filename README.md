# Handeye-Calibration-App

面向 ROS2 机械臂的 Linux 桌面手眼标定应用，提供相机内参标定、Eye-in-Hand 样本采集、手眼求解、诊断与验证的一体化工作流

## 功能

- ROS2 机器人位姿输入支持 `PoseStamped`、`TransformStamped`、TF2
- 兼容需要显式运动学模型的 `JointState` 输入和手动位姿输入
- 相机支持 ROS2 `Image`、`CameraInfo` 以及本地 V4L2 设备
- 支持 Chessboard、CharUco、相机内参标定和内参文件导入
- 保留 OpenCV、Robust、Bundle Adjustment 三种手眼求解方式
- 静止状态下采集图像与机器人位姿，提示过期帧、异常姿态和坐标系错误
- 显示、复制和导出带 Frame 定义的 4×4 手眼矩阵

## 安装和启动

Ubuntu 上准备 Python、Node.js、npm 和桌面环境

```bash
./install.sh
./launch.sh
```

使用 ROS2 数据时，应用必须运行在可访问 ROS2 网络与 Python 消息包的环境中

```bash
ROS_SETUP=/opt/ros/humble/setup.bash ./launch.sh
```

已安装 ROS2 时可以让启动脚本自动发现环境

## 使用流程

1. 连接机器人位姿和相机数据，必要时使用发现话题选择输入
2. 明确机器人末端参考 Frame，相机光学 Frame 优先从 Image 和 CameraInfo 获取
3. 选择普通棋盘格或 CharUco，并导入 CameraInfo、YAML 或重新标定内参
4. 保持标定板固定，移动机械臂至不同位姿，每次停稳后采样
5. 保存采集样本，运行 Diagnose、Solve 和 Verify
6. 查看 `parent_frame → child_frame`，复制或导出 `handeye_transform.yaml`

## 坐标系约定

`PoseStamped.header.frame_id` 是位姿表达的参考 Frame，消息不含末端 Frame，需要用户另外填写

`TransformStamped` 提供 `header.frame_id` 与 `child_frame_id`，TF2 通过配置两端 Frame 查询变换

当机器人输入为 `base → end` 且相机固定在末端时，眼在手上的结果为 `end → camera`，矩阵单位为米

应用只导出矩阵，不修改机器人 URDF、TF 或控制器配置

## 相机内参

ROS2 CameraInfo 仅支持本应用可处理的针孔相机与兼容的畸变模型，必须与采集图像分辨率一致

图像支持 `bgr8`、`rgb8`、`bgra8`、`rgba8`、`mono8` 和 `8UC1`，RGB-D 相机手眼标定无需强制订阅深度数据

使用不同设备时确认图像和位姿时间基准，静止采样采用接收时间配对与机械臂稳定性检查，不能替代运动中的硬件曝光同步

## 目录说明

- `src/renderer/` — 桌面 GUI
- `desktop/` — Electron 桌面进程
- `backend/bridge.py` — GUI 与算法接口
- `ros_interface.py` — ROS2 机器人位姿和相机输入
- `calibration_board.py` — 标定板角点与几何关系
- `calibration_engine.py` — 内参与手眼样本采集
- `algorithms/` — 标定求解、诊断、精化与结果核验
- `USER_GUIDE.md` — 操作指南
