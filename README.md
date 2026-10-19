<div align="center">

# Handeye Calibration

面向 ROS2 机器人的桌面手眼标定工具，支持眼在手上标定、独立验证和人工空间触点检查

</div>

## 功能

- 支持 Chessboard 和 CharUco 标定板，可采集、恢复、清洗并保存相机内参与手眼样本
- 相机输入支持 ROS2 Image、CameraInfo 与本地 V4L2 设备
- 机器人位姿支持 TransformStamped、PoseStamped、TF2 与 JointState + URDF
- 提供多种手眼求解方法、结果冻结、离线验证、真机几何验证与空间触点检查
- 支持导入 URDF、Description 及网格，在只读三维查看器中检查模型和坐标系
- 项目目录分别保存采样与求解结果，未求解时可确认并强制切换项目
- 空间触点检查会核对实时 RGB 尺寸、冻结尺寸、内参矩阵及畸变参数，分别显示异常原因
- 可选 RGB-D 预接近功能依赖机器人侧已有的 MoveIt 运动接口，并执行安全边界限制

## 安装

Ubuntu 下安装 Python、Node.js、npm 及桌面环境，使用 ROS2 数据时还需安装对应的 ROS2 运行环境

```bash
chmod +x ./install.sh ./launch.sh ./build_linux.sh ./start_ubuntu.sh ./uninstall.sh

./install.sh
./launch.sh
```

指定 ROS2 环境时可使用

```bash
ROS_SETUP=/opt/ros/humble/setup.bash ./launch.sh
```

## 基本流程

1. 在连接页指定项目目录，配置相机和机器人输入，搜索并选择实际 ROS2 话题
2. 连接后检查实时图像、CameraInfo、机械臂基座及末端 Frame
3. 选择标定板，导入内参或采集内参图像进行求解
4. 保持标定板固定，改变末端位置和旋转方向，停稳后采集手眼样本
5. 保存样本，在诊断与求解页面检查数据质量并求解手眼矩阵
6. 冻结结果，再使用独立样本进行离线或真机几何验证
7. 如需空间触点检查，先确认工具 Link 原点正确，人工记录参考点后采集视觉测量

## 项目与数据

- 每个项目独立存储 `calibration/`、`handeye/` 中的文件
- 仅采集尚未求解的样本也可以保留，切换项目前正常保存即可
- 强制切换前必须主动勾选确认，程序将优先保存原项目已有的可恢复样本，再卸载原项目状态
- 导入保存的 `samples.yaml` 时需保证相机内参、标定板参数及机器人和相机坐标系一致
- 分辨率改变时不自动缩放保存的内参或放宽空间验证门槛，应恢复原相机模式或重新标定

## 坐标系

眼在手上标定输出末端 Frame 到相机光学 Frame 的刚体变换矩阵，使用米作为平移单位

`TransformStamped` 提供基座和末端 Frame，`PoseStamped` 只有参考 Frame，必须额外指定末端 Frame

应用不会自动修改 URDF、发布 TF 或代替机器人控制器进行运动规划

完整操作见 [USER_GUIDE.md](USER_GUIDE.md)，实现规划见 [docs/plan.md](docs/plan.md)
