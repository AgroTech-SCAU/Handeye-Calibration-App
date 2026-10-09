from __future__ import annotations

import json
import numpy as np
import threading
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RosPose:
    values: tuple[float, float, float, float, float, float, float]
    timestamp: float
    frame_id: str
    child_frame_id: str = ""


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
        self._tf_listener = None
        self._tf_buffer = None
        self._tf_timer = None

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
        base_frame: str = "",
        end_frame: str = "",
    ) -> None:
        if self.running:
            return
        if input_type != "tf" and not input_topic.strip():
            raise ValueError("请先选择机器人位姿话题")
        try:
            import rclpy
            from geometry_msgs.msg import PoseStamped, TransformStamped
            from rclpy.executors import SingleThreadedExecutor
            from rclpy.node import Node
            from sensor_msgs.msg import JointState
            from std_msgs.msg import Bool, String
        except ImportError as exc:
            raise RuntimeError(
                "未找到 ROS2 Python 环境；请先 source ROS2 setup，并用该环境的 Python 启动 APP"
            ) from exc

        if not rclpy.ok():
            rclpy.init(args=None)
        node = Node("handeye_calibration_app")

        def pose_callback(message) -> None:
            stamp = message.header.stamp
            timestamp = float(stamp.sec) + float(stamp.nanosec) * 1e-9
            position = message.pose.position
            orientation = message.pose.orientation
            self._on_pose(
                RosPose(
                    values=(
                        float(position.x),
                        float(position.y),
                        float(position.z),
                        float(orientation.x),
                        float(orientation.y),
                        float(orientation.z),
                        float(orientation.w),
                    ),
                    timestamp=timestamp or time.time(),
                    frame_id=message.header.frame_id,
                    child_frame_id="",
                )
            )

        def transform_callback(message) -> None:
            transform = message.transform
            stamp = message.header.stamp
            timestamp = float(stamp.sec) + float(stamp.nanosec) * 1e-9
            self._on_pose(RosPose(
                values=(float(transform.translation.x), float(transform.translation.y),
                        float(transform.translation.z), float(transform.rotation.x),
                        float(transform.rotation.y), float(transform.rotation.z),
                        float(transform.rotation.w)),
                timestamp=timestamp or time.time(), frame_id=message.header.frame_id,
                child_frame_id=message.child_frame_id,
            ))

        def joints_callback(message) -> None:
            try:
                available_names = tuple(str(name) for name in message.name)
                available_values = tuple(float(value) for value in message.position)
                if joint_names:
                    value_by_name = dict(zip(available_names, available_values))
                    missing = [
                        name for name in joint_names if name not in value_by_name
                    ]
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
                self._on_joints(
                    RosJoints(
                        values=selected_values,
                        names=selected_names,
                        timestamp=timestamp or time.time(),
                        frame_id=message.header.frame_id,
                    )
                )
            except Exception as exc:
                text = str(exc)
                self._on_error(text)
                self.publish_status("input_error", error=text)

        if input_type == "pose":
            node.create_subscription(PoseStamped, input_topic, pose_callback, 20)
            message_type = "geometry_msgs/msg/PoseStamped"
        elif input_type == "transform":
            node.create_subscription(TransformStamped, input_topic, transform_callback, 20)
            message_type = "geometry_msgs/msg/TransformStamped"
        elif input_type == "tf":
            if not base_frame.strip() or not end_frame.strip() or base_frame == end_frame:
                node.destroy_node()
                raise ValueError("TF2 需要不同的基座 Frame 和末端 Frame")
            try:
                from tf2_ros import Buffer, TransformListener
                from rclpy.duration import Duration
                self._tf_buffer = Buffer()
                self._tf_listener = TransformListener(self._tf_buffer, node, spin_thread=False)
                def poll_tf():
                    try:
                        t = self._tf_buffer.lookup_transform(base_frame, end_frame, rclpy.time.Time(), timeout=Duration(seconds=0.01))
                        transform_callback(t)
                    except Exception:
                        pass  # TF tree may not be available immediately
                self._tf_timer = node.create_timer(1.0/30.0, poll_tf)
            except ImportError as exc:
                node.destroy_node()
                raise RuntimeError("TF2 输入需要安装 tf2_ros") from exc
            message_type = "tf2_ros/lookup_transform"
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
        self._thread = threading.Thread(
            target=executor.spin, daemon=True, name="ros2-spin"
        )
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
        self._tf_listener = None
        self._tf_buffer = None
        self._tf_timer = None


def decode_ros_image(message):
    """Convert common ROS2 RGB encodings to contiguous OpenCV BGR without cv_bridge"""
    encoding = str(message.encoding).lower()
    channels = {"bgr8": 3, "rgb8": 3, "bgra8": 4, "rgba8": 4, "mono8": 1, "8uc1": 1}
    if encoding not in channels:
        raise ValueError("相机图像编码不支持: " + encoding + "，请选择 RGB 图像话题")
    height, width, step = int(message.height), int(message.width), int(message.step)
    count = channels[encoding]
    if height <= 0 or width <= 0 or step < width * count:
        raise ValueError("ROS2 图像尺寸或行步长无效")
    raw = np.frombuffer(message.data, dtype=np.uint8)
    if len(raw) < height * step:
        raise ValueError("ROS2 图像数据长度不足")
    pixels = raw[:height*step].reshape(height, step)[:, :width*count]
    pixels = pixels.reshape(height, width, count)
    import cv2
    if encoding == "bgr8":
        return np.ascontiguousarray(pixels)
    code = {"rgb8": cv2.COLOR_RGB2BGR, "bgra8": cv2.COLOR_BGRA2BGR,
            "rgba8": cv2.COLOR_RGBA2BGR, "mono8": cv2.COLOR_GRAY2BGR,
            "8uc1": cv2.COLOR_GRAY2BGR}[encoding]
    return cv2.cvtColor(pixels, code)


class RosCameraInterface:
    """Independent ROS2 camera subscriber; supports camera connection before robot pose"""
    def __init__(self, on_frame, on_info, on_error):
        self.on_frame = on_frame
        self.on_info = on_info
        self.on_error = on_error
        self.node = None
        self.executor = None
        self.thread = None
        self.running = False

    def start(self, image_topic: str, info_topic: str):
        if self.running:
            return
        if not image_topic.strip():
            raise ValueError("请选择 ROS2 图像话题")
        try:
            import rclpy
            from rclpy.node import Node
            from rclpy.executors import SingleThreadedExecutor
            from rclpy.qos import qos_profile_sensor_data
            from sensor_msgs.msg import Image, CameraInfo
        except ImportError as exc:
            raise RuntimeError("无法连接 ROS2 相机，请在 ROS2 环境启动应用") from exc
        if not rclpy.ok():
            rclpy.init(args=None)
        node = Node("handeye_camera_input")
        def image_callback(msg):
            try:
                frame = decode_ros_image(msg)
                stamp = float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec)*1e-9
                self.on_frame(frame, stamp, msg.header.frame_id)
            except Exception as exc:
                self.on_error(str(exc))
        def info_callback(msg):
            try:
                self.on_info(msg)
            except Exception as exc:
                self.on_error(str(exc))
        node.create_subscription(Image, image_topic, image_callback, qos_profile_sensor_data)
        if info_topic.strip():
            node.create_subscription(CameraInfo, info_topic, info_callback, qos_profile_sensor_data)
        executor = SingleThreadedExecutor()
        executor.add_node(node)
        self.node = node
        self.executor = executor
        self.running = True
        self.thread = threading.Thread(target=executor.spin, name="ros-camera-spin", daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        executor, self.executor = self.executor, None
        node, self.node = self.node, None
        if executor is not None:
            executor.shutdown(timeout_sec=1.0)
        if node is not None:
            node.destroy_node()
        self.thread = None


def discover_ros_topics():
    """Return active topics with types, without starting any subscriptions"""
    try:
        import rclpy
        from rclpy.node import Node
    except ImportError as exc:
        raise RuntimeError("未找到 ROS2 环境，无法发现话题") from exc
    if not rclpy.ok():
        rclpy.init(args=None)
    node = Node("handeye_topic_discovery")
    try:
        rclpy.spin_once(node, timeout_sec=0.2)
        return [{"topic": name, "types": types} for name, types in sorted(node.get_topic_names_and_types())]
    finally:
        node.destroy_node()
