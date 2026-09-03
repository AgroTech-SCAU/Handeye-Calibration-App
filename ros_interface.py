from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from image_converter import image_message_to_bgr

POSE_TYPE = "geometry_msgs/msg/PoseStamped"
IMAGE_TYPE = "sensor_msgs/msg/Image"
CAMERA_INFO_TYPE = "sensor_msgs/msg/CameraInfo"


@dataclass(frozen=True)
class ContractTopics:
    pose_topics: tuple[str, ...]
    image_topics: tuple[str, ...]
    camera_info_topics: tuple[str, ...]


@dataclass(frozen=True)
class RosPose:
    values: tuple[float, float, float, float, float, float, float]
    timestamp: float
    frame_id: str


@dataclass(frozen=True)
class RosImage:
    frame: object
    timestamp: float
    frame_id: str
    encoding: str
    width: int
    height: int


@dataclass(frozen=True)
class RosCameraInfo:
    width: int
    height: int
    k: tuple[float, ...]
    d: tuple[float, ...]
    distortion_model: str
    timestamp: float
    frame_id: str


def discover_contract_topics(
    topic_names_and_types: Iterable[tuple[str, Sequence[str]]],
) -> ContractTopics:
    pose: list[str] = []
    images: list[str] = []
    camera_info: list[str] = []
    for name, types in topic_names_and_types:
        type_set = set(types)
        if POSE_TYPE in type_set:
            pose.append(str(name))
        if IMAGE_TYPE in type_set:
            images.append(str(name))
        if CAMERA_INFO_TYPE in type_set:
            camera_info.append(str(name))
    return ContractTopics(
        tuple(sorted(set(pose))),
        tuple(sorted(set(images))),
        tuple(sorted(set(camera_info))),
    )


def _stamp_to_seconds(header) -> float:
    stamp = getattr(header, "stamp", None)
    if stamp is None:
        return time.time()
    value = (
        float(getattr(stamp, "sec", 0.0)) + float(getattr(stamp, "nanosec", 0.0)) * 1e-9
    )
    return value or time.time()


class RosInterface:
    """ROS2 adapter for the v1 hand-eye calibration contract.

    The GUI only consumes standard ROS messages:
      - geometry_msgs/msg/PoseStamped
      - sensor_msgs/msg/Image
      - sensor_msgs/msg/CameraInfo (optional)
    Topic names are selected at runtime and are never fixed by the application.
    """

    def __init__(
        self,
        on_pose: Callable[[RosPose], None],
        on_image: Callable[[RosImage], None],
        on_camera_info: Callable[[RosCameraInfo], None],
        on_error: Callable[[str], None],
    ) -> None:
        self._on_pose = on_pose
        self._on_image = on_image
        self._on_camera_info = on_camera_info
        self._on_error = on_error
        self._node = None
        self._executor = None
        self._thread: threading.Thread | None = None
        self._subscriptions: list[object] = []
        self._running = False
        self._rclpy = None

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        try:
            import rclpy
            from rclpy.executors import SingleThreadedExecutor
            from rclpy.node import Node
        except ImportError as exc:
            raise RuntimeError(
                "未找到 ROS2 Python 环境；请先 source 当前 ROS2 发行版后启动应用"
            ) from exc

        if not rclpy.ok():
            rclpy.init(args=None)
        node = Node("handeye_calibration_app")
        executor = SingleThreadedExecutor()
        executor.add_node(node)
        self._rclpy = rclpy
        self._node = node
        self._executor = executor
        self._running = True
        self._thread = threading.Thread(
            target=executor.spin,
            daemon=True,
            name="handeye-ros2-spin",
        )
        self._thread.start()

    def discover_topics(self) -> ContractTopics:
        if self._node is None:
            raise RuntimeError("ROS2 尚未启动")
        return discover_contract_topics(self._node.get_topic_names_and_types())

    def subscribe(
        self,
        pose_topic: str,
        image_topic: str,
        camera_info_topic: str = "",
    ) -> None:
        if self._node is None:
            raise RuntimeError("ROS2 尚未启动")
        pose_topic = pose_topic.strip()
        image_topic = image_topic.strip()
        camera_info_topic = camera_info_topic.strip()
        if not pose_topic:
            raise ValueError("必须选择或填写 PoseStamped 话题")
        if not image_topic:
            raise ValueError("必须选择或填写 Image 话题")

        try:
            from geometry_msgs.msg import PoseStamped
            from rclpy.qos import qos_profile_sensor_data
            from sensor_msgs.msg import CameraInfo, Image
        except ImportError as exc:
            raise RuntimeError(
                "当前 ROS2 环境缺少 geometry_msgs 或 sensor_msgs"
            ) from exc

        self._clear_subscriptions()

        def pose_callback(message) -> None:
            try:
                p = message.pose.position
                q = message.pose.orientation
                self._on_pose(
                    RosPose(
                        values=(
                            float(p.x),
                            float(p.y),
                            float(p.z),
                            float(q.x),
                            float(q.y),
                            float(q.z),
                            float(q.w),
                        ),
                        timestamp=_stamp_to_seconds(message.header),
                        frame_id=str(message.header.frame_id),
                    )
                )
            except Exception as exc:  # callback errors must not kill the executor
                self._on_error(f"PoseStamped 解析失败：{exc}")

        def image_callback(message) -> None:
            try:
                frame = image_message_to_bgr(message)
                self._on_image(
                    RosImage(
                        frame=frame,
                        timestamp=_stamp_to_seconds(message.header),
                        frame_id=str(message.header.frame_id),
                        encoding=str(message.encoding),
                        width=int(message.width),
                        height=int(message.height),
                    )
                )
            except Exception as exc:
                self._on_error(f"Image 解析失败：{exc}")

        def camera_info_callback(message) -> None:
            try:
                self._on_camera_info(
                    RosCameraInfo(
                        width=int(message.width),
                        height=int(message.height),
                        k=tuple(float(v) for v in message.k),
                        d=tuple(float(v) for v in message.d),
                        distortion_model=str(message.distortion_model),
                        timestamp=_stamp_to_seconds(message.header),
                        frame_id=str(message.header.frame_id),
                    )
                )
            except Exception as exc:
                self._on_error(f"CameraInfo 解析失败：{exc}")

        self._subscriptions.append(
            self._node.create_subscription(PoseStamped, pose_topic, pose_callback, 20)
        )
        self._subscriptions.append(
            self._node.create_subscription(
                Image, image_topic, image_callback, qos_profile_sensor_data
            )
        )
        if camera_info_topic:
            self._subscriptions.append(
                self._node.create_subscription(
                    CameraInfo,
                    camera_info_topic,
                    camera_info_callback,
                    qos_profile_sensor_data,
                )
            )

    def _clear_subscriptions(self) -> None:
        if self._node is None:
            self._subscriptions.clear()
            return
        for subscription in self._subscriptions:
            try:
                self._node.destroy_subscription(subscription)
            except Exception:
                pass
        self._subscriptions.clear()

    def stop(self) -> None:
        self._running = False
        self._clear_subscriptions()
        executor, self._executor = self._executor, None
        node, self._node = self._node, None
        if executor is not None:
            try:
                executor.shutdown(timeout_sec=1.0)
            except Exception:
                pass
        if node is not None:
            try:
                node.destroy_node()
            except Exception:
                pass
        self._thread = None
