from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RosPose:
    values: tuple[float, float, float, float, float, float, float]
    timestamp: float
    frame_id: str


@dataclass(frozen=True)
class RosJoints:
    values: tuple[float, ...]
    names: tuple[str, ...]
    timestamp: float
    frame_id: str


class RosInterface:
    """ROS2 subscriptions used by automatic hand-eye sample collection.

    Inputs:
      geometry_msgs/PoseStamped or sensor_msgs/JointState input_topic
    Output:
      optional std_msgs/String status_topic (JSON status/event payload)
    """

    def __init__(
        self,
        on_pose: Callable[[RosPose], None],
        on_joints: Callable[[RosJoints], None],
        on_capture: Callable[[], None],
        on_error: Callable[[str], None],
    ):
        self._on_pose = on_pose
        self._on_joints = on_joints
        self._on_capture = on_capture
        self._on_error = on_error
        self._thread: threading.Thread | None = None
        self._executor = None
        self._node = None
        self._publisher = None
        self._String = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def start(
        self,
        input_type: str,
        input_topic: str,
        capture_topic: str,
        status_topic: str,
        joint_dof: int = 5,
        joint_names: tuple[str, ...] = (),
    ) -> None:
        if self.running:
            return
        try:
            import rclpy
            from geometry_msgs.msg import PoseStamped
            from rclpy.executors import SingleThreadedExecutor
            from rclpy.node import Node
            from sensor_msgs.msg import JointState
            from std_msgs.msg import Bool, String
        except ImportError as exc:
            raise RuntimeError(
                "未找到 ROS2 Python 环境。请先 source ROS2 setup，并用该环境的 Python 启动 APP。"
            ) from exc

        if not rclpy.ok():
            rclpy.init(args=None)
        node = Node("handeye_calibration_app")

        def pose_callback(message) -> None:
            stamp = message.header.stamp
            timestamp = float(stamp.sec) + float(stamp.nanosec) * 1e-9
            position = message.pose.position
            orientation = message.pose.orientation
            self._on_pose(RosPose(
                values=(
                    float(position.x), float(position.y), float(position.z),
                    float(orientation.x), float(orientation.y),
                    float(orientation.z), float(orientation.w),
                ),
                timestamp=timestamp or time.time(),
                frame_id=message.header.frame_id,
            ))

        def joints_callback(message) -> None:
            try:
                available_names = tuple(str(name) for name in message.name)
                available_values = tuple(float(value) for value in message.position)
                if joint_names:
                    value_by_name = dict(zip(available_names, available_values))
                    missing = [name for name in joint_names if name not in value_by_name]
                    if missing:
                        raise ValueError(f"JointState 缺少关节: {', '.join(missing)}")
                    selected_names = joint_names
                    selected_values = tuple(value_by_name[name] for name in joint_names)
                else:
                    if len(available_values) < joint_dof:
                        raise ValueError(
                            f"JointState.position 只有 {len(available_values)} 个值，"
                            f"界面配置为 {joint_dof} 自由度"
                        )
                    selected_values = available_values[:joint_dof]
                    selected_names = (
                        available_names[:joint_dof]
                        if len(available_names) >= joint_dof
                        else tuple(f"q{i + 1}" for i in range(joint_dof))
                    )
                stamp = message.header.stamp
                timestamp = float(stamp.sec) + float(stamp.nanosec) * 1e-9
                self._on_joints(RosJoints(
                    values=selected_values,
                    names=selected_names,
                    timestamp=timestamp or time.time(),
                    frame_id=message.header.frame_id,
                ))
            except Exception as exc:
                text = str(exc)
                self._on_error(text)
                self.publish_status("input_error", error=text)

        if input_type == "pose":
            node.create_subscription(PoseStamped, input_topic, pose_callback, 20)
            message_type = "geometry_msgs/msg/PoseStamped"
        elif input_type == "joints":
            node.create_subscription(JointState, input_topic, joints_callback, 20)
            message_type = "sensor_msgs/msg/JointState"
        else:
            node.destroy_node()
            raise ValueError(f"未知 ROS2 输入类型: {input_type}")
        if capture_topic:
            def capture_callback(message) -> None:
                if bool(message.data):
                    self._on_capture()
            node.create_subscription(Bool, capture_topic, capture_callback, 10)
        if status_topic:
            self._publisher = node.create_publisher(String, status_topic, 10)
            self._String = String
        executor = SingleThreadedExecutor()
        executor.add_node(node)
        self._node = node
        self._executor = executor
        self._running = True
        self._thread = threading.Thread(target=executor.spin, daemon=True, name="ros2-spin")
        self._thread.start()
        self.publish_status(
            "ros_started",
            input_type=input_type,
            input_topic=input_topic,
            message_type=message_type,
            joint_dof=joint_dof if input_type == "joints" else None,
            joint_names=list(joint_names) if joint_names else None,
            capture_mode="local_button" if not capture_topic else "ros_topic",
        )

    def publish_status(self, event: str, **fields) -> None:
        if self._publisher is None or self._String is None:
            return
        message = self._String()
        message.data = json.dumps(
            {"event": event, "timestamp": time.time(), **fields},
            ensure_ascii=False,
        )
        self._publisher.publish(message)

    def stop(self) -> None:
        self._running = False
        executor, self._executor = self._executor, None
        node, self._node = self._node, None
        if executor is not None:
            executor.shutdown(timeout_sec=1.0)
        if node is not None:
            node.destroy_node()
        self._publisher = None
        self._String = None
        self._thread = None
