#!/usr/bin/env python3
from __future__ import annotations

import base64
import builtins
from dataclasses import asdict
from functools import wraps
import itertools
import json
import math
import os
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PREVIEW_INTERVAL_SEC = 0.10
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_zip_strict_compat() -> None:
    """Backport zip(strict=True) for Ubuntu 20.04 / Python 3.8.

    Preserve support for extensions using zip(strict=True) on Python 3.8
    """
    if sys.version_info < (3, 10):
        original_zip = builtins.zip
        sentinel = object()

        def compat_zip(*iterables, strict=False):
            if not strict:
                return original_zip(*iterables)

            def strict_iter():
                for row in itertools.zip_longest(*iterables, fillvalue=sentinel):
                    if any(item is sentinel for item in row):
                        raise ValueError("zip() arguments have different lengths")
                    yield row

            return strict_iter()

        builtins.zip = compat_zip


_install_zip_strict_compat()

from algorithm_runner import joints_to_pose, run_algorithm
from calibration_engine import CameraSession, HandEyeCollection, IntrinsicCalibration, detect_chessboard, rpy_to_quaternion
from calibration_board import CalibrationBoard, positive_int
from capture_sync import PoseHistory
from config import AppConfig
from ros_interface import RosInterface, RosCameraInterface, RosJoints, RosPose, discover_ros_topics, inspect_ros_topic


class JsonOut:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Keep the protocol on the process' original stdout. The frozen
        # algorithm runner temporarily redirects sys.stdout/sys.stderr so its
        # human-readable logs can be streamed to the GUI. If protocol JSON
        # followed that redirect, log events would recursively feed themselves
        self._stream = sys.stdout

    def send(self, payload: dict[str, Any]) -> None:
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            self._stream.write(line + "\n")
            self._stream.flush()


def serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self.session_lock:
            return method(self, *args, **kwargs)
    return call


class Bridge:
    def __init__(self) -> None:
        self.session_lock = threading.RLock()
        self.ros_source = None
        self.out = JsonOut()
        self.mock = os.environ.get("HANDEYE_MOCK", "0") == "1"
        data_dir = Path(os.environ.get("HANDEYE_DATA_DIR", ROOT / ".runtime")).expanduser().resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = data_dir
        self.config_path = data_dir / "app_config.json"
        first_run = not self.config_path.exists()
        self.config = AppConfig.load(self.config_path)
        # The original main-branch GUI intentionally leaves the optional ROS
        # capture trigger empty on first run; preserve that behavior here
        if first_run:
            self.config.capture_topic = ""
        if self.mock:
            # Demonstration frames are only supplied by the offline mock backend
            self.config.robot_base_frame = self.config.robot_base_frame or "arm_base_link"
            self.config.robot_end_frame = self.config.robot_end_frame or "demo_tool"
            self.config.camera_frame = self.config.camera_frame or "demo_camera_optical_frame"
        if not self.config.output_dir or self.config.output_dir.startswith(str(ROOT)):
            self.config.output_dir = str((data_dir / "output").resolve())
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

        self.camera = CameraSession()
        self.camera_open = False
        self.current_frame: np.ndarray | None = None
        self.frame_received_at = None
        self.frame_ros_stamp = None
        self.frame_id = ""
        self.frame_lock = threading.Lock()
        self.pose_history = PoseHistory()
        self.board_found = False
        self.board_corners = None
        self.frame_counter = 0
        self.preview_seq = 0
        self.camera_info = None
        self.frame_error_at = 0.0
        self.source_frames = None
        self.intrinsic = IntrinsicCalibration()
        self.handeye = HandEyeCollection()
        self.latest_pose: RosPose | None = None
        self.latest_pose_at = None
        self.latest_robot_input: tuple[float, ...] | None = None
        self.latest_input_mode = "ros_pose"
        self.last_error = ""
        self._running = True
        self._camera_thread = threading.Thread(target=self._camera_loop, daemon=True, name="camera-preview")

        self.ros = RosInterface(
            self._on_pose,
            self._on_joints,
            self._on_capture,
            self._on_ros_error,
        )
        self.ros_camera = RosCameraInterface(self._on_image, self._on_camera_info, self._on_ros_error)
        self._camera_thread.start()

    def _paths(self) -> tuple[Path, Path, Path]:
        out = Path(self.config.output_dir).expanduser().resolve()
        return out, out / "camera_intrinsics.yaml", out / "samples.yaml"

    def _emit(self, event: str, data: Any = None) -> None:
        self.out.send({"kind": "event", "event": event, "data": data})

    def _state(self) -> dict[str, Any]:
        out, intrinsics, samples = self._paths()
        pose = None
        if self.latest_pose is not None and (self.mock or (self.latest_pose_at is not None and time.monotonic()-self.latest_pose_at < 1.5)):
            pose = {
                "values": list(self.latest_pose.values),
                "timestamp": self.latest_pose.timestamp,
                "frame_id": self.latest_pose.frame_id,
                "child_frame_id": self.latest_pose.child_frame_id or self.config.robot_end_frame,
                "input_mode": self.latest_input_mode,
            }
        return {
            "mock": self.mock,
            "config": {
                "output_dir": self.config.output_dir,
                "camera_source": self.config.camera_source,
                "image_topic": self.config.image_topic,
                "camera_info_topic": self.config.camera_info_topic,
                "camera_frame": self.config.camera_frame,
                "robot_base_frame": self.config.robot_base_frame,
                "robot_end_frame": self.config.robot_end_frame,
                "camera_index": self.config.camera_index,
                "camera_width": self.config.camera_width,
                "camera_height": self.config.camera_height,
                "chessboard_cols": self.config.chessboard_cols,
                "chessboard_rows": self.config.chessboard_rows,
                "square_size_mm": self.config.square_size_mm,
                **{key: value for key, value in asdict(self.config).items() if key.startswith("charuco_") or key == "board_type"},
                "ros_input_type": self.config.ros_input_type,
                "pose_topic": self.config.pose_topic,
                "joint_dof": self.config.joint_dof,
                "joint_names": self.config.joint_names,
                "capture_topic": self.config.capture_topic,
                "status_topic": self.config.status_topic,
            },
            "camera": {
                "open": self.camera_open,
                "receiving": bool(self.camera_open and self.current_frame is not None and
                                  self.frame_received_at is not None and
                                  time.monotonic()-self.frame_received_at < 1.5),
                "frame_id": self.frame_id,
                "camera_info_ready": self.camera_info is not None,
                "camera_info_frame": (self.camera_info or {}).get("frame_id", ""),
                "board_found": bool(self.board_found),
                        "corner_count": len(self.board_corners) if self.board_found else 0,
                "width": int(self.current_frame.shape[1]) if self.current_frame is not None else self.config.camera_width,
                "height": int(self.current_frame.shape[0]) if self.current_frame is not None else self.config.camera_height,
            },
            "ros": {
                "running": bool(self.ros.running) or (self.mock and self.latest_pose is not None),
                "pose": pose,
            },
            "intrinsics": {
                "count": len(self.intrinsic.image_sets),
                "exists": intrinsics.exists(),
                "path": str(intrinsics),
            },
            "handeye": {
                "count": len(self.handeye.samples),
                "samples_exists": samples.exists(),
                "samples_path": str(samples),
                "result_path": str(samples.with_name(f"{samples.stem}_result.yaml")),
            },
            "output_dir": str(out),
            "last_error": self.last_error,
        }

    def _emit_state(self) -> None:
        self._emit("state", self._state())

    def _mock_frame(self) -> np.ndarray:
        width = max(640, int(self.config.camera_width))
        height = max(480, int(self.config.camera_height))
        canvas = np.full((height, width, 3), 32, np.uint8)
        if self.config.board_type == "charuco":
            board = CalibrationBoard(self.config.board_config())
            bw = width-100
            bh = int(bw*self.config.charuco_squares_y/self.config.charuco_squares_x)
            if bh > height-100:
                bh = height-100
                bw = int(bh*self.config.charuco_squares_x/self.config.charuco_squares_y)
            pattern = board.board.generateImage((bw,bh), marginSize=10)
            ox,oy = (width-bw)//2,(height-bh)//2
            canvas[oy:oy+bh,ox:ox+bw] = cv2.cvtColor(pattern,cv2.COLOR_GRAY2BGR)
            return canvas
        cols, rows = self.config.chessboard_cols + 1, self.config.chessboard_rows + 1
        sq = max(20, min(width // (cols + 4), height // (rows + 4)))
        bw, bh = cols * sq, rows * sq
        ox, oy = (width - bw) // 2, (height - bh) // 2
        for r in range(rows):
            for c in range(cols):
                color = 242 if (r + c) % 2 == 0 else 15
                cv2.rectangle(canvas, (ox + c * sq, oy + r * sq), (ox + (c + 1) * sq, oy + (r + 1) * sq), (color, color, color), -1)
        cv2.putText(canvas, "SANDBOX MOCK CAMERA", (22, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (245, 158, 11), 2, cv2.LINE_AA)
        return canvas

    def _camera_loop(self) -> None:
        last_state = 0.0
        last_ros_preview_at = None
        while self._running:
            frame = None
            if self.camera_open and self.config.camera_source == "v4l2":
                frame = self._mock_frame() if self.mock else self.camera.read()
                if frame is not None:
                    with self.frame_lock:
                        self.current_frame = frame
                        self.frame_received_at = time.monotonic()
                        self.frame_ros_stamp = None
                        self.frame_id = self.config.camera_frame
            elif self.camera_open and self.mock:
                frame = self._mock_frame()
                with self.frame_lock:
                    self.current_frame = frame
                    self.frame_received_at = time.monotonic()
                    self.frame_ros_stamp = None
                    self.frame_id = self.config.camera_frame
            elif self.camera_open and self.config.camera_source == "ros":
                with self.frame_lock:
                    fresh = (self.frame_received_at is not None and
                             time.monotonic()-self.frame_received_at < 1.5 and
                             self.frame_received_at != last_ros_preview_at)
                    frame = self.current_frame.copy() if fresh and self.current_frame is not None else None
                    if fresh:
                        last_ros_preview_at = self.frame_received_at
            if frame is not None:
                self.frame_counter += 1
                if self.frame_counter % 3 == 0:
                    try:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        preview_board = CalibrationBoard(self.config.board_config())
                        detection = preview_board.detect(gray)
                        self.board_found, self.board_corners = True, detection.image_points
                        self.preview_board = preview_board
                        self.preview_detection = detection
                    except Exception:
                        self.board_found, self.board_corners = False, None
                display = frame.copy()
                if self.board_found and self.board_corners is not None:
                    self.preview_board.draw(display, self.preview_detection)
                # Keep preview responsive while limiting IPC bandwidth
                h, w = display.shape[:2]
                if w > 960:
                    scale = 960.0 / w
                    display = cv2.resize(display, (960, max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
                ok, encoded = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
                if ok:
                    self.preview_seq += 1
                    self._emit("preview", {
                        "seq": self.preview_seq,
                        "jpeg": base64.b64encode(encoded.tobytes()).decode("ascii"),
                        "board_found": bool(self.board_found),
                        "corner_count": len(self.board_corners) if self.board_found else 0,
                        "width": int(frame.shape[1]),
                        "height": int(frame.shape[0]),
                    })
            now = time.monotonic()
            if now - last_state > 1.0:
                self._emit_state()
                last_state = now
            time.sleep(PREVIEW_INTERVAL_SEC)

    def _on_image(self, frame: np.ndarray, stamp: float, frame_id: str) -> None:
        # ROS2 subscription owns the capture timestamp, not the preview thread
        old_frame = self.frame_id
        old_size = self.current_frame.shape[:2] if self.current_frame is not None else ()
        with self.frame_lock:
            self.current_frame = frame
            self.frame_received_at = time.monotonic()
            self.frame_ros_stamp = stamp if stamp > 0 else None
            self.frame_id = str(frame_id).lstrip("/")
        if old_frame != self.frame_id or old_size != frame.shape[:2]:
            self._emit("camera_metadata", {"frame_id": self.frame_id,
                                           "width": int(frame.shape[1]), "height": int(frame.shape[0])})

    def _on_camera_info(self, message) -> None:
        previous = self.camera_info
        matrix = [float(v) for v in message.k]
        distortion = [float(v) for v in message.d]
        model = str(message.distortion_model)
        if model not in ("plumb_bob", "rational_polynomial", ""):
            return  # unsupported distortion models must not be imported as pinhole coefficients
        if len(matrix) != 9 or matrix[0] <= 0 or matrix[4] <= 0 or not all(math.isfinite(x) for x in matrix + distortion):
            return
        if len(distortion) not in (4, 5, 8, 12, 14):
            return
        self.camera_info = dict(
            camera_matrix={"rows": 3, "cols": 3, "data": matrix},
            distortion_coefficients={"rows": 1, "cols": len(distortion), "data": distortion},
            image_width=int(message.width), image_height=int(message.height),
            frame_id=str(message.header.frame_id).lstrip("/"),
            distortion_model=model, origin="ROS2 CameraInfo",
        )
        if previous is None or previous.get("frame_id") != self.camera_info["frame_id"]:
            self._emit("camera_metadata", {"frame_id": self.camera_info["frame_id"],
                                           "width": int(message.width), "height": int(message.height)})

    @serialized
    def import_camera_info(self, _params: dict[str, Any]) -> dict[str, Any]:
        if self.handeye.samples:
            raise ValueError("已有外参样本，导入内参前请先清空外参样本")
        data = self.camera_info
        if not data:
            raise ValueError("尚未收到有效 CameraInfo，请检查相机内参话题及畸变模型")
        with self.frame_lock:
            frame = self.current_frame
            frame_id = self.frame_id
        if frame is None:
            raise ValueError("尚未收到相机图像")
        if [int(data['image_width']), int(data['image_height'])] != [frame.shape[1], frame.shape[0]]:
            raise ValueError("CameraInfo 分辨率与当前图像不一致")
        if frame_id and data['frame_id'] and frame_id != data['frame_id']:
            raise ValueError("CameraInfo 与 Image 的 Frame 不一致，请选择同一相机模式")
        import yaml
        _, path, _ = self._paths()
        path.parent.mkdir(parents=True, exist_ok=True)
        exported = {k: data[k] for k in ('camera_matrix','distortion_coefficients','image_width','image_height','distortion_model','origin')}
        path.write_text(yaml.safe_dump(exported, sort_keys=False, allow_unicode=True), encoding='utf-8')
        self.intrinsic = IntrinsicCalibration()
        self._emit_state()
        return {"path": str(path), "frame_id": data['frame_id']}

    @serialized
    def import_intrinsics(self, params: dict[str, Any]) -> dict[str, Any]:
        if self.handeye.samples:
            raise ValueError("已有外参样本，导入内参前请先清空外参样本")
        source = Path(str(params.get('path', ''))).expanduser().resolve()
        if not source.is_file() or source.suffix.lower() not in ('.yaml','.yml'):
            raise ValueError("请选择已有相机内参 YAML 文件")
        from calibration_engine import load_intrinsics, intrinsic_binding
        import yaml
        _, _, data = load_intrinsics(source)
        intrinsic_binding(data)
        _, target, _ = self._paths()
        target.parent.mkdir(parents=True, exist_ok=True)
        if source != target:
            target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding='utf-8')
        self.intrinsic = IntrinsicCalibration()
        self._emit_state()
        return {"path": str(target)}

    def _on_pose(self, pose: RosPose) -> None:
        if self.config.ros_input_type == "pose" and not self.config.robot_end_frame:
            self._on_ros_error("PoseStamped 不包含末端 Frame，请先填写末端 Frame")
            return
        if self.config.ros_input_type in ("transform", "tf") and not pose.child_frame_id:
            self._on_ros_error("TransformStamped 缺少 child_frame_id")
            return
        if self.config.robot_base_frame and pose.frame_id and pose.frame_id.lstrip('/') != self.config.robot_base_frame.lstrip('/'):
            self._on_ros_error("机器人基座 Frame 与收到的消息不一致")
            return
        child = pose.child_frame_id or self.config.robot_end_frame
        if self.config.ros_input_type == "transform" and self.config.robot_end_frame and child != self.config.robot_end_frame:
            self._on_ros_error("末端 Frame 与收到的 TransformStamped 不一致")
            return
        if not pose.frame_id or not child or pose.frame_id == child:
            self._on_ros_error("末端位姿的基座或末端 Frame 无效")
            return
        current_frames = (pose.frame_id.lstrip('/'), child.lstrip('/'))
        if self.handeye.samples and self.source_frames and self.source_frames[:2] != current_frames:
            self._on_ros_error("机器人坐标系已变化，请清空外参样本后重新采集")
            return
        if self.latest_pose and (self.latest_pose.frame_id, self.latest_pose.child_frame_id or self.config.robot_end_frame) != (pose.frame_id, child):
            self.pose_history.clear()
        pose = RosPose(pose.values, pose.timestamp, current_frames[0], current_frames[1])
        try:
            self.pose_history.add(pose.values, time.monotonic(), pose.timestamp, pose.values, "ros_pose")
        except ValueError as exc:
            self._emit("error", {"message": str(exc)})
            return
        self.latest_pose = pose
        self.latest_pose_at = time.monotonic()
        self.latest_robot_input = pose.values
        self.latest_input_mode = "ros_pose"
        self._emit("pose", {
            "values": list(pose.values), "timestamp": pose.timestamp,
            "frame_id": pose.frame_id, "child_frame_id": pose.child_frame_id, "input_mode": self.latest_input_mode,
        })

    def _on_joints(self, joints: RosJoints) -> None:
        try:
            pose_values = joints_to_pose(joints.values)
            self.pose_history.add(pose_values, time.monotonic(), joints.timestamp, joints.values, "ros_joints")
            self.latest_pose = RosPose(pose_values, joints.timestamp, joints.frame_id or self.config.robot_base_frame, self.config.robot_end_frame)
            self.latest_pose_at = time.monotonic()
            self.latest_robot_input = joints.values
            self.latest_input_mode = "ros_joints"
            self._emit("pose", {
                "values": list(pose_values), "timestamp": joints.timestamp,
                "frame_id": joints.frame_id or self.config.robot_base_frame, "child_frame_id": self.config.robot_end_frame, "input_mode": self.latest_input_mode,
                "joint_names": list(joints.names), "joints": list(joints.values),
            })
        except Exception as exc:
            self._on_ros_error(str(exc))

    def _on_capture(self) -> None:
        try:
            result = self.capture_handeye({"mode": "auto", "quality_mode": "standard"})
            self._emit("capture", result)
        except Exception as exc:
            self._emit("error", {"message": str(exc)})

    def _on_ros_error(self, text: str) -> None:
        self.last_error = text
        self._emit("error", {"message": text})

    @serialized
    def _apply_config(self, params: dict[str, Any]) -> dict[str, Any]:
        values = asdict(self.config)
        integer_fields = {"camera_index", "camera_width", "camera_height", "chessboard_cols", "chessboard_rows", "joint_dof", "charuco_squares_x", "charuco_squares_y", "charuco_min_corners"}
        for key, value in params.items():
            if key not in values:
                continue
            if key in integer_fields:
                value = positive_int(value, key, 0 if key == "camera_index" else 1)
            elif key in {"square_size_mm", "charuco_marker_size_mm"}:
                if isinstance(value, bool):
                    raise ValueError("尺寸必须是数值")
                value = float(value)
            elif key == "charuco_legacy_pattern":
                if not isinstance(value, bool):
                    raise ValueError("legacy_pattern 必须是布尔值")
            else:
                value = str(value)
            values[key] = value
        candidate = AppConfig(**values)
        CalibrationBoard(candidate.board_config())
        if candidate.camera_source not in ("ros", "v4l2"):
            raise ValueError("相机输入只能是 ROS2 或 V4L2")
        if candidate.ros_input_type not in ("pose", "transform", "tf", "joints"):
            raise ValueError("机器人输入类型无效")
        for key in ("robot_base_frame", "robot_end_frame", "camera_frame"):
            frame = getattr(candidate, key).strip().lstrip('/')
            if any(c.isspace() for c in frame):
                raise ValueError("Frame 名称不能包含空白字符")
            setattr(candidate, key, frame)
        changed = {key for key in values if values[key] != getattr(self.config, key)}
        acquisition = {"output_dir", "camera_source", "image_topic", "camera_info_topic", "camera_frame", "robot_base_frame", "robot_end_frame", "camera_index", "camera_width", "camera_height", "chessboard_cols", "chessboard_rows", "square_size_mm", "board_type", "ros_input_type", "pose_topic", "joint_dof", "joint_names"} | {k for k in values if k.startswith("charuco_")}
        if changed & acquisition and (self.intrinsic.image_sets or self.handeye.samples):
            raise ValueError("采集会话中不能更换板参数、相机、位姿来源或输出目录，请先清空采集")
        camera_fields = {"camera_source", "image_topic", "camera_info_topic", "camera_index", "camera_width", "camera_height"}
        if self.camera_open and changed & camera_fields:
            raise ValueError("更换相机配置前请关闭相机")
        if self.ros.running and changed & {"ros_input_type", "pose_topic", "robot_base_frame", "robot_end_frame", "joint_dof", "joint_names"}:
            raise ValueError("更换位姿来源前请断开 ROS")
        Path(candidate.output_dir).expanduser().mkdir(parents=True, exist_ok=True)
        candidate.save(self.config_path)
        self.config = candidate
        if changed & acquisition:
            self.board_found, self.board_corners = False, None
            with self.frame_lock:
                self.current_frame, self.frame_received_at = None, None
            self.pose_history.clear()
            self.camera_info = None
        return self._state()

    @serialized
    def connect_robot(self, _params: dict[str, Any]) -> dict[str, Any]:
        """Connect the selected pose source and camera together, with rollback"""
        c = self.config
        expected = {
            "pose": "geometry_msgs/msg/PoseStamped",
            "transform": "geometry_msgs/msg/TransformStamped",
            "joints": "sensor_msgs/msg/JointState",
        }
        if c.camera_source == "ros" and not c.image_topic.strip():
            raise ValueError("请选择相机 Image 话题")
        if c.ros_input_type != "tf" and not c.pose_topic.strip():
            raise ValueError("请选择机械臂位姿话题")
        if c.ros_input_type == "pose" and not c.robot_end_frame:
            raise ValueError("PoseStamped 不携带末端 Frame，请填写末端 Frame")
        if c.ros_input_type in ("tf", "joints") and (not c.robot_base_frame or not c.robot_end_frame):
            raise ValueError("请填写基座 Frame 与末端 Frame")
        if c.camera_source == "ros" and c.camera_frame and c.camera_info_topic and self.camera_info:
            known = self.camera_info.get("frame_id", "")
            if known and known != c.camera_frame:
                raise ValueError("CameraInfo Frame 与配置的相机 Frame 不一致")
        if not self.mock:
            graph = {record["topic"]: record["types"] for record in discover_ros_topics()}
            required = [(c.image_topic, "sensor_msgs/msg/Image")] if c.camera_source == "ros" else []
            if c.camera_source == "ros" and c.camera_info_topic:
                required.append((c.camera_info_topic, "sensor_msgs/msg/CameraInfo"))
            if c.ros_input_type != "tf":
                required.append((c.pose_topic, expected[c.ros_input_type]))
            if c.capture_topic:
                required.append((c.capture_topic, "std_msgs/msg/Bool"))
            for name, kind in required:
                if kind not in graph.get(name, []):
                    raise ValueError(f"话题 {name} 不存在或消息类型不匹配，需要 {kind}，请重新搜索话题")
        was_ros = bool(self.ros.running)
        was_camera = self.camera_open
        try:
            if not was_ros:
                self.start_ros({})
            if not was_camera:
                self.open_camera({})
        except Exception:
            if not was_camera and self.camera_open:
                self.close_camera({})
            if not was_ros and self.ros.running:
                self.stop_ros({})
            raise
        self._emit_state()
        return self._state()

    @serialized
    def disconnect_robot(self, _params: dict[str, Any]) -> dict[str, Any]:
        if self.camera_open:
            self.close_camera({})
        if self.ros.running or self.latest_pose is not None:
            self.stop_ros({})
        self._emit_state()
        return self._state()

    @serialized
    def open_camera(self, _params: dict[str, Any]) -> dict[str, Any]:
        if not self.mock:
            if self.config.camera_source == 'ros':
                self.ros_camera.start(self.config.image_topic, self.config.camera_info_topic)
            else:
                self.camera.open(self.config.camera_index, self.config.camera_width, self.config.camera_height)
        self.camera_open = True
        self._emit_state()
        return self._state()["camera"]

    @serialized
    def close_camera(self, _params: dict[str, Any]) -> dict[str, Any]:
        self.ros_camera.stop()
        self.camera.close()
        self.camera_open = False
        with self.frame_lock:
            self.current_frame = None
            self.frame_received_at = None
            self.frame_ros_stamp = None
            self.frame_id = ""
        self.camera_info = None
        self.board_found = False
        self._emit_state()
        return self._state()["camera"]

    @serialized
    def capture_intrinsic(self, params: dict[str, Any]) -> dict[str, Any]:
        if self.current_frame is None:
            raise RuntimeError("请先打开相机并等待实时画面")
        mode = str(params.get("quality_mode", "standard"))
        result = self.intrinsic.add(
            self.current_frame.copy(), self.config.chessboard_cols,
            self.config.chessboard_rows, self.config.square_size_mm,
            quality_mode=mode, board=self.config.board_config(),
        )
        payload = {
            "count": len(self.intrinsic.image_sets),
            "sharpness": result.sharpness,
            "board_coverage_percent": result.board_coverage_percent,
        }
        self._emit("intrinsic", payload)
        self._emit_state()
        return payload

    @serialized
    def clear_intrinsic(self, _params: dict[str, Any]) -> dict[str, Any]:
        self.intrinsic = IntrinsicCalibration()
        self._emit_state()
        return {"count": 0}

    @serialized
    def solve_intrinsic(self, params: dict[str, Any]) -> dict[str, Any]:
        if self.handeye.samples:
            raise ValueError("已有外参样本，重新标定内参前请先清空外参样本")
        _, path, _ = self._paths()
        result = self.intrinsic.solve(
            path, self.config.chessboard_cols, self.config.chessboard_rows,
            self.config.square_size_mm,
            quality_mode=str(params.get("quality_mode", "standard")), board=self.config.board_config(),
        )
        self._emit("intrinsic_solved", result)
        self._emit_state()
        return result

    @serialized
    def start_ros(self, params: dict[str, Any]) -> dict[str, Any]:
        input_type = str(params.get("input_type", self.config.ros_input_type))
        input_topic = str(params.get("input_topic", self.config.pose_topic)).strip()
        capture_topic = str(params.get("capture_topic", self.config.capture_topic)).strip()
        status_topic = str(params.get("status_topic", self.config.status_topic)).strip()
        joint_dof = int(params.get("joint_dof", self.config.joint_dof))
        names_raw = params.get("joint_names", self.config.joint_names)
        if isinstance(names_raw, str):
            joint_names = tuple(x.strip() for x in names_raw.split(",") if x.strip())
        else:
            joint_names = tuple(str(x) for x in names_raw or [])
        base_frame = self.config.robot_base_frame
        end_frame = self.config.robot_end_frame
        if input_type == "pose" and not end_frame:
            raise ValueError("PoseStamped 无法携带末端 Frame，请填写末端 Frame")
        if input_type == "tf" and (not base_frame or not end_frame):
            raise ValueError("TF2 需要填写基座和末端 Frame")
        if input_type == "joints" and (not base_frame or not end_frame):
            raise ValueError("JointState 需要配置运动学参考坐标系，请填写基座和末端 Frame")
        source = (input_type, input_topic, base_frame, end_frame, joint_dof if input_type == "joints" else None, joint_names if input_type == "joints" else ())
        if self.handeye.samples and source != self.ros_source:
            raise ValueError("已有外参样本，更换位姿来源前请先清空样本")
        if self.ros.running and source != self.ros_source:
            raise ValueError("更换位姿来源前请断开 ROS")
        self.pose_history.clear()
        if self.mock:
            self.latest_pose = RosPose((0.412, -0.083, 0.536, 0.012, 0.713, 0.008, 0.701), time.time(), base_frame or "base_link", end_frame or "tool0")
            self.latest_robot_input = self.latest_pose.values
            self.latest_input_mode = "ros_pose"
            self._on_pose(self.latest_pose)
        else:
            self.ros.start(input_type, input_topic, capture_topic, status_topic, joint_dof, joint_names, base_frame, end_frame)
        self.ros_source = source
        self._emit_state()
        return self._state()["ros"]

    @serialized
    def stop_ros(self, _params: dict[str, Any]) -> dict[str, Any]:
        if not self.mock:
            self.ros.stop()
        self.latest_pose = None
        self.latest_pose_at = None
        self.pose_history.clear()
        self.latest_robot_input = None
        if not self.handeye.samples:
            self.source_frames = None
        self._emit_state()
        return self._state()["ros"]

    def _manual_pose(self, params: dict[str, Any]) -> tuple[tuple[float, ...], tuple[float, ...], str]:
        kind = str(params.get("manual_type", "quaternion"))
        values = tuple(float(v) for v in params.get("values", []))
        unit = str(params.get("angle_unit", "deg"))
        scale = math.pi / 180.0 if unit == "deg" else 1.0
        if kind == "quaternion":
            if len(values) != 7:
                raise ValueError("四元数模式需要 x y z qx qy qz qw 共 7 个值")
            return values, values, "pose"
        if kind == "rpy":
            if len(values) != 6:
                raise ValueError("RPY 模式需要 x y z roll pitch yaw 共 6 个值")
            x, y, z, roll, pitch, yaw = values
            q = rpy_to_quaternion(roll * scale, pitch * scale, yaw * scale)
            return (x, y, z, *q), values, "pose_rpy"
        if kind == "joints":
            joints = tuple(v * scale for v in values)
            return joints_to_pose(joints), joints, "joints"
        raise ValueError(f"未知手动输入模式: {kind}")

    @serialized
    def capture_handeye(self, params: dict[str, Any]) -> dict[str, Any]:
        with self.frame_lock:
            frame = None if self.current_frame is None else self.current_frame.copy()
            frame_time = self.frame_received_at
            frame_stamp = self.frame_ros_stamp
            image_frame = self.frame_id
        if frame is None:
            raise RuntimeError("请先打开相机并等待实时画面")
        if frame_time is None or time.monotonic()-frame_time > .5:
            raise ValueError("相机帧已过期")
        mode = str(params.get("mode", "auto"))
        if mode == "auto":
            if self.latest_pose is None:
                raise RuntimeError("尚未收到 ROS2 机器人位姿")
            entry, sync_dt = self.pose_history.match(frame_time, time.monotonic())
            pose = entry["pose"]
            robot_input = entry["robot_input"] or pose
            timestamp = entry["robot_timestamp"]
            input_mode = entry["input_mode"]
        else:
            pose, robot_input, input_mode = self._manual_pose(params)
            timestamp = time.time()
        if mode == "auto":
            if not self.latest_pose or not self.latest_pose.child_frame_id:
                raise ValueError("无法确定机械臂末端坐标系")
            robot_base, robot_end = self.latest_pose.frame_id, self.latest_pose.child_frame_id
        else:
            robot_base, robot_end = self.config.robot_base_frame, self.config.robot_end_frame
        camera_frame = self.config.camera_frame or image_frame or (self.camera_info or {}).get('frame_id', '')
        if not robot_base or not robot_end or not camera_frame:
            raise ValueError("请明确机器人基座、末端和相机光学 Frame")
        frames = (robot_base, robot_end, camera_frame)
        if self.source_frames is not None and self.handeye.samples and frames != self.source_frames:
            raise ValueError("采集坐标系已变化，请清空外参样本后重新采集")
        if self.config.camera_frame and image_frame and self.config.camera_frame != image_frame:
            raise ValueError("用户配置的相机 Frame 与 Image 消息不一致")
        _, intrinsics, _ = self._paths()
        if not intrinsics.exists():
            raise FileNotFoundError("请先完成内参标定，缺少 camera_intrinsics.yaml")
        if mode == "auto" and frame_stamp is not None and timestamp is not None and abs(frame_stamp-timestamp) < 1 and abs(frame_stamp-timestamp) > .1:
            raise ValueError("ROS2 图像和机器人位姿的时间戳相差过大，请检查时间同步")
        quality = str(params.get("quality_mode", "standard"))
        result = self.handeye.add(
            frame, pose, intrinsics,
            self.config.chessboard_cols, self.config.chessboard_rows,
            self.config.square_size_mm, input_mode, timestamp,
            robot_pose_input=robot_input, quality_mode=quality, board=self.config.board_config(),
        )
        self.source_frames = frames
        self.handeye.samples[-1].update(robot_base_frame=robot_base, robot_end_frame=robot_end, camera_frame=camera_frame)
        if mode == "auto":
            is_shared_clock = frame_stamp is not None and timestamp is not None and abs(frame_stamp - timestamp) < 1
            self.handeye.samples[-1].update(sync_frame_pose_dt_ms=sync_dt, sync_robot_stable=True,
                sync_time_basis="ros_header_and_stopped" if is_shared_clock else "host_receipt_and_stopped",
                image_stamp=frame_stamp)
        payload = {
            "count": len(self.handeye.samples),
            "reprojection_error_px": result.reprojection_error_px,
            "distance_mm": result.distance_mm,
            "sharpness": result.sharpness,
            "pixels_per_square": result.pixels_per_square,
        }
        self.ros.publish_status("sample_captured", sample_count=payload["count"], reprojection_error_px=result.reprojection_error_px)
        self._emit("handeye", payload)
        self._emit_state()
        return payload

    @serialized
    def clear_samples(self, _params: dict[str, Any]) -> dict[str, Any]:
        self.handeye = HandEyeCollection()
        self.source_frames = None
        self._emit_state()
        return {"count": 0}

    @serialized
    def save_samples(self, _params: dict[str, Any]) -> dict[str, Any]:
        _, intrinsics, samples = self._paths()
        self.handeye.save(
            samples, intrinsics, self.config.chessboard_cols,
            self.config.chessboard_rows, self.config.square_size_mm, board=self.config.board_config(),
        )
        import yaml
        document = yaml.safe_load(samples.read_text(encoding="utf-8"))
        base, end, cam = self.source_frames or (self.config.robot_base_frame, self.config.robot_end_frame, self.config.camera_frame)
        if not base or not end or not cam:
            raise ValueError("采样坐标系不完整")
        document.update(robot_base_frame=base, robot_end_frame=end, camera_frame=cam)
        samples.write_text(yaml.safe_dump(document, sort_keys=False, allow_unicode=True), encoding="utf-8")
        self.ros.publish_status("samples_saved", path=str(samples), count=len(self.handeye.samples))
        self._emit_state()
        return {"path": str(samples), "count": len(self.handeye.samples)}

    @serialized
    def run_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        name = str(params.get("name", "solve"))
        mode = str(params.get("solve_mode", "robust"))
        _, _, samples = self._paths()
        if not samples.exists():
            raise FileNotFoundError("请先保存外参样本 samples.yaml")
        chunks: list[str] = []
        def emit(text: str) -> None:
            chunks.append(text)
            self._emit("log", {"text": text})
        code = run_algorithm(name, samples, mode, emit)
        result_path = samples.with_name(f"{samples.stem}_result.yaml")
        payload = {"name": name, "exit_code": code, "ok": code == 0, "result_path": str(result_path), "log": "".join(chunks)}
        if name == "solve" and code == 0 and result_path.exists():
            try:
                import yaml
                payload["result"] = yaml.safe_load(result_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        self._emit("tool_done", payload)
        self._emit_state()
        return payload

    @serialized
    def export_matrix(self, _params: dict[str, Any]) -> dict[str, Any]:
        import yaml
        out, _, samples = self._paths()
        result_path = samples.with_name(f"{samples.stem}_result.yaml")
        if not result_path.exists():
            raise FileNotFoundError("尚无手眼求解结果")
        result = yaml.safe_load(result_path.read_text(encoding='utf-8')) or {}
        matrix = np.asarray(result.get('transform_matrix'), dtype=np.float64)
        parent, child = result.get('parent_frame'), result.get('child_frame')
        if matrix.shape != (4,4) or not np.isfinite(matrix).all() or not parent or not child:
            raise ValueError("手眼结果缺少有效矩阵或坐标系")
        if str(parent).startswith('UNRESOLVED_') or str(child).startswith('UNRESOLVED_'):
            raise ValueError("历史样本缺少坐标系元数据，请确认 Frame 后重新采集")
        if not np.allclose(matrix[3], [0,0,0,1]):
            raise ValueError("手眼矩阵最后一行无效")
        export = dict(parent_frame=parent, child_frame=child,
            transform_matrix=matrix.tolist(), translation_unit='m',
            method=result.get('method'), sample_count=result.get('inlier_count'),
            translation_rms_mm=result.get('translation_rms_mm'),
            rotation_rms_deg=result.get('rotation_rms_deg'))
        path = out / 'handeye_transform.yaml'
        path.write_text(yaml.safe_dump(export, sort_keys=False, allow_unicode=True), encoding='utf-8')
        return {"path": str(path), "result": export}

    def dispatch(self, method: str, params: dict[str, Any]) -> Any:
        if method == "ping":
            return {"pong": True, "python": sys.version.split()[0], "mock": self.mock}
        if method == "get_state":
            return self._state()
        if method == "set_config":
            return self._apply_config(params)
        if method == "discover_topics":
            return {"topics": [] if self.mock else discover_ros_topics()}
        if method == "inspect_topic":
            if self.mock:
                return {"received": False, "metadata": {}}
            topic = str(params.get("topic", ""))
            kind = str(params.get("message_type", ""))
            graph = {record["topic"]: record["types"] for record in discover_ros_topics()}
            if kind not in graph.get(topic, []):
                raise ValueError("选择的话题不存在或类型不匹配，请重新搜索")
            return inspect_ros_topic(topic, kind)
        if method == "connect_robot":
            return self.connect_robot(params)
        if method == "disconnect_robot":
            return self.disconnect_robot(params)
        if method == "import_camera_info":
            return self.import_camera_info(params)
        if method == "import_intrinsics":
            return self.import_intrinsics(params)
        if method == "open_camera":
            return self.open_camera(params)
        if method == "close_camera":
            return self.close_camera(params)
        if method == "capture_intrinsic":
            return self.capture_intrinsic(params)
        if method == "clear_intrinsic":
            return self.clear_intrinsic(params)
        if method == "solve_intrinsic":
            return self.solve_intrinsic(params)
        if method == "start_ros":
            return self.start_ros(params)
        if method == "stop_ros":
            return self.stop_ros(params)
        if method == "capture_handeye":
            return self.capture_handeye(params)
        if method == "clear_samples":
            return self.clear_samples(params)
        if method == "save_samples":
            return self.save_samples(params)
        if method == "export_matrix":
            return self.export_matrix(params)
        if method == "run_tool":
            return self.run_tool(params)
        if method == "shutdown":
            self.shutdown()
            return {"ok": True}
        raise ValueError(f"未知请求: {method}")

    def serve(self) -> None:
        self._emit("ready", self._state())
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            req_id = None
            try:
                request = json.loads(line)
                req_id = request.get("id")
                result = self.dispatch(str(request.get("method", "")), dict(request.get("params") or {}))
                self.out.send({"kind": "response", "id": req_id, "ok": True, "result": result})
            except Exception as exc:
                self.last_error = str(exc)
                self.out.send({
                    "kind": "response", "id": req_id, "ok": False,
                    "error": str(exc), "trace": traceback.format_exc(limit=4),
                })
                self._emit("error", {"message": str(exc)})
        self.shutdown()

    def shutdown(self) -> None:
        self._running = False
        if self._camera_thread.is_alive() and self._camera_thread is not threading.current_thread():
            self._camera_thread.join(timeout=2.0)
        try:
            self.ros_camera.stop()
            self.camera.close()
        except Exception:
            pass
        try:
            self.ros.stop()
        except Exception:
            pass


def main() -> None:
    Bridge().serve()


if __name__ == "__main__":
    main()
