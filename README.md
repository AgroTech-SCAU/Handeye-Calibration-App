# Handeye-Calibration-App

通用 ROS2 眼在手上标定桌面应用，独立于机械臂品牌、控制器与机器人系统集成框架

## 功能

- ROS2 机器人位姿输入支持 `PoseStamped`、`TransformStamped`、TF2
- 支持 `JointState + URDF` 正运动学和手动位姿输入，不再使用内置示例机械臂参数
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
7. 保存训练样本，在「诊断与求解」页面完成数据诊断、样本清洗和矩阵求解
8. 点击「使用当前求解矩阵」，冻结手眼矩阵和训练棋盘参考
9. 进入「验证」，导入独立验证样本或连接机械臂采集新验证样本
10. 生成 `validation_report.yaml`，检查全部样本误差后导出手眼矩阵

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
- `algorithms/` — 标定求解、诊断与精化
- `validation_engine.py` — 独立离线与真机验证、报告计算
- `USER_GUIDE.md` — 操作指南

Tomato-Manipulation 的手眼标定节点可发布 `/arm/tool_transform`，输入类型选择 `TransformStamped` 后搜索并选择该话题

## 样本清洗与继续采集

手眼采样页面可导入之前保存的 `samples.yaml`

导入时核对标定板、冻结内参、机械臂坐标系、相机坐标系及样本矩阵，恢复原有质量模式，并允许继续采集

手眼采样页和诊断与求解页都能根据稳定样本 ID 删除异常样本，删除后更新 `samples.yaml` 并使旧求解结果失效

清洗前的文件保留为 `samples.backup.yaml`

极简建议 8 组，标准建议 20 组，严格建议 30 组，达到数量不等于满足旋转激励及求解质量要求

诊断、手眼求解、离线与真机验证、相机内参求解在独立进程运行，可以通过进度弹窗取消，已存在的有效计算结果不会因取消而覆盖

## 独立验证

「诊断与求解」只负责对训练样本诊断、清洗和求解，验证在第五个独立页面完成

求解后点击「使用当前求解矩阵」，应用创建 `validation_reference.yaml`，记录 `tool0 → camera` 等实际 Frame、冻结矩阵、相机内参、棋盘参数、训练样本签名以及由训练数据估计的固定棋盘参考

**离线验证**

- 不需要连接机器人或相机，选择未参与求解的新采集 `samples.yaml`
- 自动拒绝训练与验证样本重叠、Frame 不一致、内参不一致和棋盘规格不一致
- 通过固定矩阵和固定参考计算每个样本的平移、旋转和预测角点误差，并保存 `validation_offline_report.yaml`

**真机验证**

- 保持标定板位置不动并连接机械臂和相机
- 进入「验证 → 真机验证」，实时预览叠加实测角点与固定参考预测角点
- 人工移动机械臂，停稳后采集验证样本，验证样本保存为 `validation_samples.yaml`
- 点击「开始验证」，输出 `validation_live_report.yaml`、逐样本误差和趋势图

离线和真机报告分别保存，`validation_report.yaml` 始终指向最近完成的一次验证

两种模式都不重新求解矩阵，也不会发出任何机械臂运动命令

验证参考来自训练数据而非独立测量真值，因此报告只评价手眼几何一致性与投影一致性，不可直接解释为绝对空间定位精度

修改训练样本、求解结果或棋盘参数后，旧冻结参考与验证报告会自动失效

## 机械臂模型与空间定位

机械臂输入可以选择 `TransformStamped`、`PoseStamped`、TF2 或 `JointState + URDF`，前三种直接提供末端位姿，导入 URDF 后可在应用内部推导与末端通过固定关节连接的 `tip` 等工具 Link

`JointState` 必须先导入真实的 URDF，使用关节名称匹配及 URDF 正运动学，不使用自带演示用的机械臂参数，导入 URDF 不会发布 `/tf`

机器人接口可选择 Description 文件夹或 ZIP，也可导入 URDF / Xacro 文件，或读取 ROS2 `/robot_description`

导入前须断开机械臂连接，系统会保存模型及其网格资源的本地副本，基础标定无需导入模型

导入模型后点击「查看三维模型」，可查看 Visual / Collision、Link / Joint 树、关节轴、工具坐标系以及有效求解矩阵对应的相机和历史棋盘位置，支持旋转、缩放、平移和刷新姿态

模型查看器通过 WebGL 在 GPU 上绘制连续网格，参考 SerialArm-Core 的只读模型检查方式，显示 Link 与关节坐标系，不使用逐三角面抽样造成网格缺口；静态几何数据会被缓存

左键拖动旋转模型，拖动方向与模型可见运动方向一致；右键或 Shift + 拖动平移，滚轮缩放，双击恢复合适视角；坐标轴颜色固定为 X 红、Y 绿、Z 蓝，关节轴为橙色；WebGL 不可用时自动进入低精度 Canvas 模式，并在顶部提示

只有完整 JointState 才能正确还原动态整臂姿态，单独的 TransformStamped、PoseStamped 或末端 TF2 不能反推出各关节角，查看器会显示 URDF 零位示意并明确标注

缺少 Mesh 只影响外观显示，不影响已知 Link 变换或基本手眼标定，GLB/OBJ/glTF 网格预览需要安装 trimesh，STL 可以直接加载

验证页面依次提供「离线验证 — 独立样本几何一致性」「真机验证 — 几何一致性」「真机验证 — 手眼伺服定位」

手眼伺服定位目前提供人工触点对照：选择工具 Link 和标定板角点 ID，手动接触停稳后记录基座参考位置，移开机械臂后用 RGB + 棋盘 PnP 重新测量同一角点，结果保存在输出目录 `spatial_contact.yaml` 和 `spatial_validation_report.yaml`

人工触点参考依赖机器人正运动学及工具安装精度，不等于第三方独立真值，自动 RGB-D 闭环伺服仅在界面说明接口要求，尚未启用机器人运动控制
