#!/usr/bin/env python3
from __future__ import annotations

import base64
import builtins
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

    The frozen GitHub-main calibration core uses ``zip(..., strict=True)``.
    Keeping the core byte-identical means compatibility belongs in this GUI
    bridge rather than in ``calibration_engine.py``.
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
from config import AppConfig
from ros_interface import RosInterface, RosJoints, RosPose


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


class Bridge:
    def __init__(self) -> None:
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
        if not self.config.output_dir or self.config.output_dir.startswith(str(ROOT)):
            self.config.output_dir = str((data_dir / "output").resolve())
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

        self.camera = CameraSession()
        self.camera_open = False
        self.current_frame: np.ndarray | None = None
        self.board_found = False
        self.board_corners = None
        self.frame_counter = 0
        self.preview_seq = 0
        self.intrinsic = IntrinsicCalibration()
        self.handeye = HandEyeCollection()
        self.latest_pose: RosPose | None = None
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
        self._camera_thread.start()

    def _paths(self) -> tuple[Path, Path, Path]:
        out = Path(self.config.output_dir).expanduser().resolve()
        return out, out / "camera_intrinsics.yaml", out / "samples.yaml"

    def _emit(self, event: str, data: Any = None) -> None:
        self.out.send({"kind": "event", "event": event, "data": data})

    def _state(self) -> dict[str, Any]:
        out, intrinsics, samples = self._paths()
        pose = None
        if self.latest_pose is not None:
            pose = {
                "values": list(self.latest_pose.values),
                "timestamp": self.latest_pose.timestamp,
                "frame_id": self.latest_pose.frame_id,
                "input_mode": self.latest_input_mode,
            }
        return {
            "mock": self.mock,
            "config": {
                "output_dir": self.config.output_dir,
                "camera_index": self.config.camera_index,
                "camera_width": self.config.camera_width,
                "camera_height": self.config.camera_height,
                "chessboard_cols": self.config.chessboard_cols,
                "chessboard_rows": self.config.chessboard_rows,
                "square_size_mm": self.config.square_size_mm,
                "ros_input_type": self.config.ros_input_type,
                "pose_topic": self.config.pose_topic,
                "joint_dof": self.config.joint_dof,
                "joint_names": self.config.joint_names,
                "capture_topic": self.config.capture_topic,
                "status_topic": self.config.status_topic,
            },
            "camera": {
                "open": self.camera_open,
                "board_found": bool(self.board_found),
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
        while self._running:
            frame = None
            if self.camera_open:
                if self.mock:
                    frame = self._mock_frame()
                else:
                    frame = self.camera.read()
            if frame is not None:
                self.current_frame = frame
                self.frame_counter += 1
                if self.frame_counter % 3 == 0:
                    try:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        self.board_found, self.board_corners = detect_chessboard(
                            gray, (self.config.chessboard_cols, self.config.chessboard_rows)
                        )
                    except Exception:
                        self.board_found, self.board_corners = False, None
                display = frame.copy()
                if self.board_found and self.board_corners is not None:
                    cv2.drawChessboardCorners(
                        display,
                        (self.config.chessboard_cols, self.config.chessboard_rows),
                        self.board_corners,
                        True,
                    )
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
                        "width": int(frame.shape[1]),
                        "height": int(frame.shape[0]),
                    })
            now = time.monotonic()
            if now - last_state > 1.0:
                self._emit_state()
                last_state = now
            time.sleep(PREVIEW_INTERVAL_SEC)

    def _on_pose(self, pose: RosPose) -> None:
        self.latest_pose = pose
        self.latest_robot_input = pose.values
        self.latest_input_mode = "ros_pose"
        self._emit("pose", {
            "values": list(pose.values), "timestamp": pose.timestamp,
            "frame_id": pose.frame_id, "input_mode": self.latest_input_mode,
        })

    def _on_joints(self, joints: RosJoints) -> None:
        try:
            pose_values = joints_to_pose(joints.values)
            self.latest_pose = RosPose(pose_values, joints.timestamp, joints.frame_id)
            self.latest_robot_input = joints.values
            self.latest_input_mode = "ros_joints"
            self._emit("pose", {
                "values": list(pose_values), "timestamp": joints.timestamp,
                "frame_id": joints.frame_id, "input_mode": self.latest_input_mode,
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

    def _apply_config(self, params: dict[str, Any]) -> dict[str, Any]:
        fields = self.config.__dataclass_fields__
        for key, value in params.items():
            if key not in fields:
                continue
            if key in {"camera_index", "camera_width", "camera_height", "chessboard_cols", "chessboard_rows", "joint_dof"}:
                value = int(value)
            elif key == "square_size_mm":
                value = float(value)
            else:
                value = str(value)
            setattr(self.config, key, value)
        Path(self.config.output_dir).expanduser().mkdir(parents=True, exist_ok=True)
        self.config.save(self.config_path)
        return self._state()

    def open_camera(self, _params: dict[str, Any]) -> dict[str, Any]:
        if not self.mock:
            self.camera.open(self.config.camera_index, self.config.camera_width, self.config.camera_height)
        self.camera_open = True
        self._emit_state()
        return self._state()["camera"]

    def close_camera(self, _params: dict[str, Any]) -> dict[str, Any]:
        self.camera.close()
        self.camera_open = False
        self.current_frame = None
        self.board_found = False
        self._emit_state()
        return self._state()["camera"]

    def capture_intrinsic(self, params: dict[str, Any]) -> dict[str, Any]:
        if self.current_frame is None:
            raise RuntimeError("请先打开相机并等待实时画面")
        mode = str(params.get("quality_mode", "standard"))
        result = self.intrinsic.add(
            self.current_frame.copy(), self.config.chessboard_cols,
            self.config.chessboard_rows, self.config.square_size_mm,
            quality_mode=mode,
        )
        payload = {
            "count": len(self.intrinsic.image_sets),
            "sharpness": result.sharpness,
            "board_coverage_percent": result.board_coverage_percent,
        }
        self._emit("intrinsic", payload)
        self._emit_state()
        return payload

    def clear_intrinsic(self, _params: dict[str, Any]) -> dict[str, Any]:
        self.intrinsic = IntrinsicCalibration()
        self._emit_state()
        return {"count": 0}

    def solve_intrinsic(self, params: dict[str, Any]) -> dict[str, Any]:
        _, path, _ = self._paths()
        result = self.intrinsic.solve(
            path, self.config.chessboard_cols, self.config.chessboard_rows,
            self.config.square_size_mm,
            quality_mode=str(params.get("quality_mode", "standard")),
        )
        self._emit("intrinsic_solved", result)
        self._emit_state()
        return result

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
        if self.mock:
            self.latest_pose = RosPose((0.412, -0.083, 0.536, 0.012, 0.713, 0.008, 0.701), time.time(), "arm_base_link")
            self.latest_robot_input = self.latest_pose.values
            self.latest_input_mode = "ros_pose"
            self._on_pose(self.latest_pose)
        else:
            self.ros.start(input_type, input_topic, capture_topic, status_topic, joint_dof, joint_names)
        self._emit_state()
        return self._state()["ros"]

    def stop_ros(self, _params: dict[str, Any]) -> dict[str, Any]:
        if not self.mock:
            self.ros.stop()
        self.latest_pose = None
        self.latest_robot_input = None
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

    def capture_handeye(self, params: dict[str, Any]) -> dict[str, Any]:
        if self.current_frame is None:
            raise RuntimeError("请先打开相机并等待实时画面")
        mode = str(params.get("mode", "auto"))
        if mode == "auto":
            if self.latest_pose is None:
                raise RuntimeError("尚未收到 ROS2 机器人位姿")
            pose = self.latest_pose.values
            robot_input = self.latest_robot_input or pose
            timestamp = self.latest_pose.timestamp
            input_mode = self.latest_input_mode
        else:
            pose, robot_input, input_mode = self._manual_pose(params)
            timestamp = time.time()
        _, intrinsics, _ = self._paths()
        if not intrinsics.exists():
            raise FileNotFoundError("请先完成内参标定，缺少 camera_intrinsics.yaml")
        quality = str(params.get("quality_mode", "standard"))
        result = self.handeye.add(
            self.current_frame.copy(), pose, intrinsics,
            self.config.chessboard_cols, self.config.chessboard_rows,
            self.config.square_size_mm, input_mode, timestamp,
            robot_pose_input=robot_input, quality_mode=quality,
        )
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

    def clear_samples(self, _params: dict[str, Any]) -> dict[str, Any]:
        self.handeye = HandEyeCollection()
        self._emit_state()
        return {"count": 0}

    def save_samples(self, _params: dict[str, Any]) -> dict[str, Any]:
        _, intrinsics, samples = self._paths()
        self.handeye.save(
            samples, intrinsics, self.config.chessboard_cols,
            self.config.chessboard_rows, self.config.square_size_mm,
        )
        self.ros.publish_status("samples_saved", path=str(samples), count=len(self.handeye.samples))
        self._emit_state()
        return {"path": str(samples), "count": len(self.handeye.samples)}

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
        if result_path.exists():
            try:
                import yaml
                payload["result"] = yaml.safe_load(result_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        self._emit("tool_done", payload)
        self._emit_state()
        return payload

    def dispatch(self, method: str, params: dict[str, Any]) -> Any:
        if method == "ping":
            return {"pong": True, "python": sys.version.split()[0], "mock": self.mock}
        if method == "get_state":
            return self._state()
        if method == "set_config":
            return self._apply_config(params)
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
        try:
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
