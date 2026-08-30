# 手眼标定工作站

这是将原 `calib` 流程集中后的独立 GUI APP，同一份代码支持 Windows 和 Ubuntu。采集、诊断、求解和验证代码均位于本目录，复制整个 `handeye_calibration_app` 文件夹即可移植。流程在界面中固定为：

1. 相机内参标定；
2. 手眼外参采样（ROS2 自动或手动输入，可使用末端位姿或关节角）；
3. 调用 APP 内置的 `algorithms/diagnose.py`、`solve.py`、`verify.py` 诊断、求解和验证。

默认是眼在手上（eye-in-hand），结果为 `^gripper T_camera`。输出文件统一放到界面选择的输出目录：

```text
camera_intrinsics.yaml
samples.yaml
samples_result.yaml
```

## ROS2 消息接口

自动模式使用 ROS2 接收机器人数据；输入类型、输入话题和可选状态话题由用户填写。采集直接点击界面“记录当前位姿样本”，不需要采集触发接口。填写后点“保存设置”可供下次启动继续使用。

| 方向 | 默认话题 | 消息类型 | 说明 |
|---|---|---|---|
| 输入（二选一） | `/arm/pose` | `geometry_msgs/msg/PoseStamped` | 机械臂末端在基座坐标系中的位置和姿态 |
| 输入（二选一） | `/arm/joint_states` | `sensor_msgs/msg/JointState` | 机械臂关节角，`position` 单位必须是 rad |
| 输出（可选） | `/handeye/status` | `std_msgs/msg/String` | JSON 状态，包括 `ros_started`、`sample_captured`、`capture_failed`、`samples_saved` |

接口和本地采集按钮的方向与意义：

- 输入话题由机器人节点发布、APP 订阅。它持续提供当前机器人状态，但不会自行保存样本；
- 采集不需要 ROS2 触发接口。机械臂停稳后直接点击界面“记录当前位姿样本”，每次点击只保存一组；
- 状态返回话题为可选，由 APP 发布、外部流程订阅。内容是 JSON，供自动流程判断连接、采集结果和失败原因；即使不填写，顶部反馈栏仍会显示全部结果。

连接成功后可用以下命令检查：

```bash
ros2 topic echo /arm/pose
ros2 topic echo /arm/joint_states
ros2 topic echo /handeye/status
```

确保机械臂已经停止且棋盘格检测状态为绿色后，点击“记录当前位姿样本”。APP 使用最新机器人消息和当前相机帧生成一组样本，成功或失败原因显示在外参页顶部。

### 外参采样质量模式

| 模式 | 重投影误差 | 清晰度 | 棋盘每格像素 | 用途 |
|---|---:|---:|---:|---|
| 标准质量（推荐） | ≤0.40 px | ≥80 | ≥20 px | 日常正式标定 |
| 严格质量 | ≤0.25 px | ≥120 | ≥25 px | 光照和相机条件较好时的高质量数据 |
| 极简采样 | 不门禁 | 不门禁 | 不门禁 | 只要求棋盘检测和 PnP 成功，用于排障 |

极简采样可能保存模糊、距离过远或重投影误差偏大的数据，不建议直接用于最终部署。

### 自动模式参数含义

选择“末端位姿（PoseStamped）”时：

- `position.x/y/z`：末端相对机械臂基座的位置，单位 m；
- `orientation.x/y/z/w`：末端姿态四元数，顺序 xyzw；
- `header.frame_id`：建议填写机械臂基座坐标系，例如 `arm_base_link`。

手眼标定不能只提供 xyz 位置：求解还需要末端旋转，因此“位置模式”实际必须提供完整的 `PoseStamped`（位置 + 姿态），或者提供关节角让 APP 通过 FK 计算完整位姿。

选择“关节角（JointState）”时：

- “关节自由度”：参与正运动学的关节数量；随附 `robot_params.yaml` 是当前机械臂的 5 自由度示例；
- `position`：关节角数组，单位必须是 rad；
- “关节顺序”：可填写逗号分隔的消息关节名，例如 `joint1,joint2,joint3,joint4,joint5`。填写后 APP 按名称重排；留空则读取 `position` 前 N 项；
- 其他自由度机器人必须同步填写对应数量，并修改 `algorithms/robot_params.yaml` 中的 MDH 参数、符号、零位偏置和工具变换。

### 手动模式选择

| 模式 | 输入参数 | 说明 |
|---|---|---|
| 末端位姿（四元数） | `x y z qx qy qz qw` | xyz 单位 m，四元数顺序 xyzw |
| 末端位姿（RPY 欧拉角） | `x y z roll pitch yaw` | xyz 单位 m；角度可选 deg 或 rad；旋转顺序为 `Rz(yaw) Ry(pitch) Rx(roll)` |
| 关节角 | `q1 ... qN` | 自由度 N 可填写；角度可选 deg 或 rad；APP 使用内置 MDH 正运动学转换为末端位姿 |

手动关节角模式同样受 `robot_params.yaml` 限制。默认模型是 5 自由度，不能只把界面自由度改成 6 而不补充第 6 轴的机器人参数。

## Ubuntu 启动

需要 Python 3.10+、Tk、ROS2 和相机访问权限：

```bash
cd handeye_calibration_app
python3 -m pip install -r requirements.txt
chmod +x start_ubuntu.sh
./start_ubuntu.sh
```

如果 ROS2 不在默认位置：

```bash
ROS_SETUP=~/ros2_ws/install/setup.bash ./start_ubuntu.sh
```

Ubuntu 缺少 Tk 时安装 `python3-tk`。当前用户还需有 `/dev/video*` 的访问权限。

## Windows 启动

在已经配置 ROS2 的命令提示符中：

```bat
cd handeye_calibration_app
python -m pip install -r requirements.txt
start_windows.bat
```

也可以设置 ROS2 环境脚本后双击启动：

```bat
set ROS_SETUP=C:\dev\ros2_humble\local_setup.bat
start_windows.bat
```

Windows 自动模式需要使用与所装 ROS2 版本兼容的 Python。若普通 Python 能启动 GUI、但提示找不到 `rclpy`，应从 ROS2 命令行启动，不能用 `pip install rclpy` 代替。

依赖文件将 OpenCV 限定为 4.x，因为求解使用 `cv2.calibrateHandEye`；某些 OpenCV 5 发行包不再提供该接口。

## 使用要点

- “角点列/行”填棋盘内角点数，不是方格数；内参与外参必须使用同一块棋盘和相同参数。
- 内参与外参都是按钮单次采集：内参点击“拍摄当前棋盘图”，外参点击“记录当前位姿样本”；每次点击只加入当前一张图片或一组样本。
- 内参标准模式至少 10 张，严格模式至少 15 张，建议采集 20～30 张并覆盖不同区域、距离和倾角；极简模式至少 3 张，只用于排障。
- 外参建议采集 20～30 组，棋盘固定不动，机械臂每次绕不同轴改变姿态后再采集。
- 求解页可选择“标准鲁棒求解（推荐）”“极简 OpenCV 求解”或“标准求解 + Bundle Adjustment”。
- 求解和验证在后台运行，完整输出显示在第三页日志框中。

### 内参采样质量模式

| 模式 | 清晰度 | 棋盘画面覆盖 | 最少图片 | 求解特点 |
|---|---:|---:|---:|---|
| 标准质量（推荐） | ≥80 | ≥3% | 10 | 固定 K3，适合正常标定 |
| 严格质量 | ≥120 | ≥6% | 15 | 固定 K3，使用更高质量图片 |
| 极简采集 | 不门禁 | 不门禁 | 3 | 使用 OpenCV 默认模型，用于快速排障 |

## APP 目录结构

```text
handeye_calibration_app/
├─ app.py                    GUI 和流程控制
├─ calibration_engine.py     内参与外参采样算法
├─ ros_interface.py          ROS2 消息接口
├─ assets/                   透明小甲鱼图案及授权说明
├─ algorithms/               诊断、手眼求解、BA 和验证算法
├─ start_windows.bat
└─ start_ubuntu.sh
```

## 可执行程序打包

分别运行 `build_windows.bat` 或 `build_ubuntu.sh`。ROS2 包含较多本机动态库，自动模式运行时仍建议从已 `source/call` ROS2 环境的终端启动打包结果。

顶部默认使用项目生成的透明小甲鱼标定助手 `assets/turtle_mascot_v2.png`；旧版 OpenMoji 图案作为回退资源保留，其授权信息见 `assets/ATTRIBUTION.md`。
