# Handeye-Calibration-App

通用 ROS2 眼在手上标定桌面应用，独立于机械臂品牌、控制器与机器人系统集成框架

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
chmod +x ./install.sh ./launch.sh

./install.sh
./launch.sh
```

使用 ROS2 数据时，应用必须运行在可访问 ROS2 网络与 Python 消息包的环境中

```bash
ROS_SETUP=/opt/ros/humble/setup.bash ./launch.sh
```

已安装 ROS2 时可以让启动脚本自动发现环境

## 使用流程

1. 在连接页面设置输出目录，在统一机器人接口中选择相机输入与机械臂位姿来源
2. 点击「搜索话题」，从按消息类型过滤的下拉列表选择 Image、CameraInfo 与机械臂位姿话题
3. 机械臂位姿优先选择 `TransformStamped`，自动从消息获取基座及末端 Frame，`PoseStamped` 兼容模式下才需填写末端 Frame
4. 点击「连接机器人」，应用先检查必填信息和话题类型，再同时连接位姿与相机，并在收到图像后开启实时预览
5. 选择普通棋盘格或 CharUco，并导入 CameraInfo、YAML 或重新标定内参
6. 保持标定板固定，移动机械臂至不同位姿，每次停稳后采样
7. 保存采集样本，运行 Diagnose、Solve 和 Verify
8. 查看 `parent_frame → child_frame`，复制或导出 `handeye_transform.yaml`

## 坐标系约定

`PoseStamped.header.frame_id` 是位姿表达的参考 Frame，消息不含末端 Frame，需要用户另外填写

`TransformStamped` 提供 `header.frame_id` 与 `child_frame_id`，软件以收到的消息为准且不允许手动覆盖，TF2 通过配置两端 Frame 查询变换

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

Tomato-Manipulation 的手眼标定节点可发布 `/arm/tool_transform`，输入类型选择 `TransformStamped` 后搜索并选择该话题

## 样本清洗与继续采集

手眼采样页面可导入之前保存的 `samples.yaml`

导入时核对标定板、冻结内参、机械臂坐标系、相机坐标系及样本矩阵，恢复原有质量模式，并允许继续采集

手眼采样页和求解与验证页都能根据稳定样本 ID 删除异常样本，删除后更新 `samples.yaml` 并使旧求解结果失效

清洗前的文件保留为 `samples.backup.yaml`

极简建议 8 组，标准建议 20 组，严格建议 30 组，达到数量不等于满足旋转激励及求解质量要求

诊断、手眼求解、验证、相机内参求解在独立进程运行，可以通过进度弹窗取消，已存在的有效计算结果不会因取消而覆盖
