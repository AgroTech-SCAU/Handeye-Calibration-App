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
import shutil
import subprocess
import tempfile
import uuid
import pickle
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any

import cv2
import yaml
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

from algorithm_runner import run_algorithm
from robot_model import RobotModel, pose_from_matrix
from description_loader import stage_description, preview_payload
from calibration_engine import CameraSession, HandEyeCollection, IntrinsicCalibration, detect_chessboard, rpy_to_quaternion
from calibration_board import CalibrationBoard, positive_int
from validation_engine import (freeze_solution, load_frozen, validate_metadata,
    evaluate_dataset, evaluate_sample, sample_signature, digest)


BOARD_FIELDS = frozenset({
    "board_type", "chessboard_cols", "chessboard_rows", "square_size_mm",
    "charuco_squares_x", "charuco_squares_y", "charuco_marker_size_mm",
    "charuco_dictionary", "charuco_min_corners", "charuco_legacy_pattern",
})


def available_aruco_dictionaries():
    aruco = getattr(cv2, "aruco", None)
    if aruco is None:
        return []
    series = ("4X4", "5X5", "6X6", "7X7")
    sizes = ("50", "100", "250", "1000")
    names = [f"DICT_{family}_{size}" for family in series for size in sizes]
    names += ["DICT_ARUCO_ORIGINAL", "DICT_APRILTAG_16h5", "DICT_APRILTAG_25h9",
              "DICT_APRILTAG_36h10", "DICT_APRILTAG_36h11"]
    return [name for name in names if hasattr(aruco, name)]
from capture_sync import PoseHistory
from config import AppConfig
from ros_interface import RosInterface, RosCameraInterface, RosDepthInterface, RosJoints, RosPose, discover_ros_topics, inspect_ros_topic
from servo_engine import depth_at, pixel_to_point, camera_to_base, project_base, make_template, track_template, limited_step
from ros_motion import MoveGroupMotion


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
        self.robot_model = None
        self.robot_model_error = ''
        self.latest_joint_positions = {}
        self.latest_joint_received_at = None
        if self.config.robot_model_path:
            try:
                self.robot_model = RobotModel.from_file(self.config.robot_model_path)
            except Exception as exc:
                self.robot_model_error = str(exc)
        self.spatial_contact = None
        self.spatial_measurements = []
        self.servo_target = None
        self.servo_motion = None
        self.servo_thread = None
        self.servo_cancel = threading.Event()
        self.servo_progress = {'phase':'idle','step':0,'message':'尚未选择目标'}
        self.servo_history = []
        self.depth_frame = None
        self.depth_stamp = None
        self.depth_frame_id = ''
        self.depth_received_at = None
        # The original main-branch GUI intentionally leaves the optional ROS
        # capture trigger empty on first run; preserve that behavior here
        if first_run:
            self.config.capture_topic = ""
        if self.mock:
            # Demonstration frames are only supplied by the offline mock backend
            self.config.robot_base_frame = self.config.robot_base_frame or "arm_base_link"
            self.config.robot_end_frame = self.config.robot_end_frame or "demo_tool"
            self.config.camera_frame = self.config.camera_frame or "demo_camera_optical_frame"
        # Keep explicit output directories across restarts, even inside the source tree
        # Redirect only the untouched first-run default to user data
        if not self.config.output_dir or (
            first_run and Path(self.config.output_dir).expanduser().resolve() == (ROOT / "output").resolve()
        ):
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
        self.samples_dirty = False
        self.validation_collection = HandEyeCollection()
        self.validation_source = ''
        self.validation_reports = {'offline': None, 'live': None}
        self.validation_live_preview = None
        self.validation_overlay_enabled = False
        self.spatial_overlay_enabled = False
        self.active_job = None
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
        self.ros_depth = RosDepthInterface(self._on_depth, self._on_ros_error)
        self._restore_project_session()
        self._restore_validation_session()
        self._camera_thread.start()

    def _intrinsic_capture_path(self, directory: Path | None = None) -> Path:
        base = Path(directory) if directory is not None else self._paths()[0]
        return base / ".handeye_intrinsic_captures.npz"

    def _persist_intrinsic_captures(self) -> None:
        """Save unfinished intrinsics without solving and without pickle data."""
        path = self._intrinsic_capture_path()
        if not self.intrinsic.image_sets:
            path.unlink(missing_ok=True)
            return
        count = len(self.intrinsic.image_sets)
        if count != len(self.intrinsic.object_sets):
            raise ValueError("内参图片采集记录不完整，已取消项目切换")
        meta = dict(count=count, board=self.intrinsic.board_spec,
                    image_size=self.intrinsic.image_size, quality_mode=self.intrinsic.quality_mode)
        arrays = {"metadata": np.frombuffer(json.dumps(meta, ensure_ascii=False).encode("utf-8"), dtype=np.uint8)}
        for i, (obj, img) in enumerate(zip(self.intrinsic.object_sets, self.intrinsic.image_sets)):
            arrays[f"object_{i}"] = np.asarray(obj)
            arrays[f"image_{i}"] = np.asarray(img)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".pending")
        try:
            with temporary.open("wb") as stream:
                np.savez_compressed(stream, **arrays)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    def _load_intrinsic_captures(self, directory: Path) -> IntrinsicCalibration:
        session = IntrinsicCalibration()
        path = self._intrinsic_capture_path(directory)
        if not path.is_file():
            return session
        with np.load(path, allow_pickle=False) as stored:
            meta = json.loads(stored["metadata"].tobytes().decode("utf-8"))
            count = int(meta["count"])
            if not 0 <= count <= 10000:
                raise ValueError("目标项目内参采样数量无效")
            session.board_spec = meta["board"]
            session.image_size = tuple(meta["image_size"])
            session.quality_mode = meta["quality_mode"]
            for i in range(count):
                session.object_sets.append(np.array(stored[f"object_{i}"], copy=True))
                session.image_sets.append(np.array(stored[f"image_{i}"], copy=True))
        return session

    @staticmethod
    def _project_board_settings(directory: Path) -> dict[str, Any] | None:
        """Read project-local board geometry before restoring its session."""
        board = None
        samples_file = directory / "samples.yaml"
        if samples_file.is_file():
            doc = yaml.safe_load(samples_file.read_text(encoding="utf-8")) or {}
            board = doc.get("board")
        snapshot_file = directory / ".handeye_intrinsic_captures.npz"
        if board is None and snapshot_file.is_file():
            with np.load(snapshot_file, allow_pickle=False) as archive:
                meta = json.loads(archive["metadata"].tobytes().decode("utf-8"))
                board = meta.get("board")
        if not board:
            return None
        CalibrationBoard(board)
        if board["type"] == "chessboard":
            return dict(board_type="chessboard", chessboard_cols=int(board["cols"]),
                        chessboard_rows=int(board["rows"]), square_size_mm=float(board["square_size_mm"]))
        return dict(board_type="charuco", charuco_squares_x=int(board["squares_x"]),
                    charuco_squares_y=int(board["squares_y"]), square_size_mm=float(board["square_size_mm"]),
                    charuco_marker_size_mm=float(board["marker_size_mm"]), charuco_dictionary=str(board["dictionary"]),
                    charuco_min_corners=int(board["min_corners"]), charuco_legacy_pattern=bool(board["legacy_pattern"]))

    def _read_project_session(self, directory: Path, config: AppConfig):
        """Validate the destination before changing the current project."""
        from calibration_engine import load_intrinsics, intrinsic_binding
        intrinsic = self._load_intrinsic_captures(directory)
        samples_file = directory / "samples.yaml"
        handeye = HandEyeCollection()
        frames = None
        if samples_file.is_file():
            data = yaml.safe_load(samples_file.read_text(encoding="utf-8")) or {}
            samples = data.get("samples") or []
            if samples:
                if data.get("board") != config.board_config():
                    raise ValueError("目标项目的标定板参数与当前配置不同，请先设置相同的标定板参数，再切换项目")
                _, _, intr_data = load_intrinsics(directory / "camera_intrinsics.yaml")
                binding = intrinsic_binding(intr_data)
                frozen_size = data.get("image_size_at_collection")
                if (frozen_size != binding["image_size"] or
                        not np.allclose(data["camera_matrix_at_collection"]["data"], binding["camera_matrix"], atol=1e-9, rtol=0) or
                        not np.allclose(data["distortion_at_collection"]["data"], binding["distortion"], atol=1e-9, rtol=0)):
                    raise ValueError("目标项目样本与其内参文件不一致，未切换项目")
                handeye.samples = samples
                handeye.quality_mode = data.get("collection_quality_mode") or samples[0].get("quality_mode", "standard")
                handeye.board_spec = data["board"]
                handeye.binding = binding
                handeye.intrinsics_snapshot = intr_data
                frames = (data.get("robot_base_frame"), data.get("robot_end_frame"), data.get("camera_frame"))
                if not all(frames):
                    raise ValueError("目标项目的样本缺少坐标系，未切换项目")
        if intrinsic.image_sets and intrinsic.board_spec != config.board_config():
            raise ValueError("目标项目未完成的内参采样使用了不同的标定板，请先匹配标定板设置")
        return intrinsic, handeye, frames

    def _restore_project_session(self) -> None:
        try:
            intrinsic, handeye, frames = self._read_project_session(self._paths()[0], self.config)
        except Exception as exc:
            self.last_error = f"当前项目保存的数据未能恢复：{exc}"
            return
        self.intrinsic = intrinsic
        self.handeye = handeye
        self.source_frames = frames
        self.samples_dirty = False

    @serialized
    def switch_project(self, params: dict[str, Any]) -> dict[str, Any]:
        """Explicit project switching, never implicitly starting a solver."""
        if set(params) - {"output_dir", "force_switch"}:
            raise ValueError("切换项目只接受输出目录与强制切换确认")
        return self._apply_config(params)

    def _spatial_camera_diagnostics(self) -> dict[str, Any]:
        """Report which camera contract differs instead of one ambiguous error."""
        from calibration_engine import load_intrinsics
        from validation_engine import load_frozen, _intrinsics
        reference, _, _ = self._validation_paths()
        if not reference.is_file():
            raise ValueError("请先冻结手眼求解结果，再检查针尖测量相机配置")
        frozen = load_frozen(reference)
        _, path, _ = self._paths()
        if not path.is_file():
            raise ValueError(f"当前项目缺少相机内参文件：{path}")
        k, d, file_metadata = load_intrinsics(path)
        fixed_k, fixed_d, fixed_size = _intrinsics(frozen)
        with self.frame_lock:
            frame = self.current_frame
            current_frame = self.frame_id
            current_size = [int(frame.shape[1]), int(frame.shape[0])] if frame is not None else None
        info = self.camera_info
        file_size = [int(file_metadata.get("image_width", 0)), int(file_metadata.get("image_height", 0))]
        camera_info_size = ([int(info["image_width"]), int(info["image_height"])] if info else None)
        def equal_array(a, b):
            return np.asarray(a).shape == np.asarray(b).shape and bool(np.allclose(a,b,atol=1e-8,rtol=0))
        problems = []
        if current_size is None:
            problems.append("未收到实时 RGB 图像，请检查当前相机来源和 Image 话题")
        elif current_size != fixed_size:
            problems.append(f"实时 RGB 图像尺寸 {current_size[0]}×{current_size[1]}，冻结结果要求 {fixed_size[0]}×{fixed_size[1]}")
        if file_size != fixed_size:
            problems.append(f"内参文件尺寸 {file_size[0]}×{file_size[1]}，冻结结果要求 {fixed_size[0]}×{fixed_size[1]}")
        if not equal_array(k, fixed_k):
            problems.append(f"当前内参文件的 K 矩阵不同，最大差值 {float(np.max(np.abs(k-fixed_k))):.8g}")
        if not equal_array(d.reshape(-1), fixed_d.reshape(-1)):
            problems.append("当前内参文件的畸变参数 D 与冻结结果不同")
        if camera_info_size and current_size and camera_info_size != current_size:
            problems.append(f"ROS CameraInfo 尺寸 {camera_info_size[0]}×{camera_info_size[1]} 与实时 RGB 图像不一致")
        if current_frame and current_frame != frozen["camera_frame"]:
            problems.append(f"RGB 光学 Frame {current_frame} 与冻结结果 {frozen['camera_frame']} 不同")
        if info and current_frame and info.get("frame_id") and info["frame_id"] != current_frame:
            problems.append(f"CameraInfo 光学 Frame {info['frame_id']} 与 RGB Image 不同")
        return dict(ok=not problems, problems=problems, image_size=current_size,
                    frozen_size=fixed_size, file_size=file_size,
                    camera_info_size=camera_info_size, image_frame=current_frame,
                    camera_info_frame=info.get("frame_id") if info else None,
                    image_topic=self.config.image_topic if self.config.camera_source == "ros" else f"V4L2 camera {self.config.camera_index}",
                    camera_info_topic=self.config.camera_info_topic if self.config.camera_source == "ros" else None,
                    intrinsics_path=str(path),
                    camera_matrix_matches=equal_array(k,fixed_k),
                    distortion_matches=equal_array(d.reshape(-1),fixed_d.reshape(-1)))

    @serialized
    def check_spatial_camera(self, _params: dict[str, Any]) -> dict[str, Any]:
        return self._spatial_camera_diagnostics()

    def _paths(self) -> tuple[Path, Path, Path]:
        out = Path(self.config.output_dir).expanduser().resolve()
        return out, out / "camera_intrinsics.yaml", out / "samples.yaml"

    def _restore_validation_session(self):
        ref, saved, _ = self._validation_paths()
        if not ref.is_file() or not saved.is_file():
            return
        try:
            from calibration_engine import load_intrinsics, intrinsic_binding
            fixed = load_frozen(ref)
            document = yaml.safe_load(saved.read_text(encoding='utf-8')) or {}
            validate_metadata(fixed, document)
            signatures = [sample_signature(item) for item in document.get('samples', [])]
            if any(sig in fixed['training_sample_signatures'] for sig in signatures):
                return
            _, intrinsic_path, _ = self._paths()
            _, _, data = load_intrinsics(intrinsic_path)
            session = HandEyeCollection()
            session.samples = document.get('samples', [])
            session.quality_mode = document.get('collection_quality_mode', 'minimal')
            session.board_spec = document['board']
            session.binding = intrinsic_binding(data)
            session.intrinsics_snapshot = data
            self.validation_collection = session
            self.validation_live_preview = evaluate_dataset(fixed, document, mode='live')
        except Exception:
            pass

    def _validation_report_path(self, mode):
        return self._paths()[0] / f'validation_{mode}_report.yaml'

    def _validation_paths(self):
        out, _, _ = self._paths()
        return (out / 'validation_reference.yaml', out / 'validation_samples.yaml',
                out / 'validation_report.yaml')

    @staticmethod
    def _compact_validation_report(report):
        if not report:
            return None
        return {**report, 'samples': [
            {key: value for key, value in sample.items() if key not in ('observed_px','predicted_px')}
            for sample in report.get('samples', [])
        ]}

    def _validation_state(self):
        ref, samples, report = self._validation_paths()
        status = 'unavailable'
        frozen = None
        if ref.is_file():
            try:
                frozen = load_frozen(ref)
                status = 'ready'
            except Exception:
                status = 'stale'
        reports = {}
        if status == 'ready':
            for mode in ('offline', 'live'):
                doc = self.validation_reports.get(mode)
                path = self._validation_report_path(mode)
                if doc is None and path.is_file():
                    try:
                        doc = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
                    except Exception:
                        doc = None
                if doc and doc.get('fixed_reference_sha256') == digest(frozen):
                    reports[mode] = self._compact_validation_report(doc)
        return {'live_preview': self._compact_validation_report(self.validation_live_preview) if status == 'ready' else None, 'reference_status': status, 'frames': [frozen[k] for k in ('robot_end_frame','camera_frame')] if frozen else [],
                'train_count': frozen.get('training_sample_count',0) if frozen else 0,
                'live_count': len(self.validation_collection.samples),
                'import_path': self.validation_source, 'live_samples_path': str(samples),
                'reference_path': str(ref), 'report_path': str(report),
                'reports': reports, 'report': next(iter(reports.values()), None),
                'overlay_enabled': self.validation_overlay_enabled}

    def _invalidate_validation(self):
        self._cancel_servo_internal()
        self.servo_target=None
        ref, _, report = self._validation_paths()
        ref.unlink(missing_ok=True)
        report.unlink(missing_ok=True)
        for mode in ('offline', 'live'):
            self._validation_report_path(mode).unlink(missing_ok=True)
        self.validation_collection = HandEyeCollection()
        self.validation_source = ''
        self.validation_reports = {'offline': None, 'live': None}
        self.validation_live_preview = None
        self.validation_overlay_enabled = False
        self.spatial_overlay_enabled = False
        self.spatial_contact=None
        self.spatial_measurements=[]

    def _emit(self, event: str, data: Any = None) -> None:
        self.out.send({"kind": "event", "event": event, "data": data})

    def _saved_samples_match_board(self, path: Path) -> bool:
        if not path.is_file():
            return False
        try:
            import yaml
            metadata = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            board = metadata.get("board")
            if board:
                return board == self.config.board_config()
            if self.config.board_type != "chessboard":
                return False
            expected = f"{self.config.chessboard_cols}x{self.config.chessboard_rows}"
            return (metadata.get("chessboard") == expected and
                    float(metadata.get("square_size_mm", -1)) == self.config.square_size_mm)
        except Exception:
            return False

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
            "aruco_dictionaries": available_aruco_dictionaries(),
            "config": {
                "output_dir": self.config.output_dir,
                "camera_source": self.config.camera_source,
                "image_topic": self.config.image_topic,
                "camera_info_topic": self.config.camera_info_topic,
                "aligned_depth_topic": self.config.aligned_depth_topic,
                "motion_action": self.config.motion_action,
                "motion_group": self.config.motion_group,
                "camera_frame": self.config.camera_frame,
                "robot_base_frame": pose["frame_id"] if self.config.ros_input_type == "transform" and pose is not None else ("" if self.config.ros_input_type == "transform" else self.config.robot_base_frame),
                "robot_end_frame": pose["child_frame_id"] if self.config.ros_input_type == "transform" and pose is not None else ("" if self.config.ros_input_type == "transform" else self.config.robot_end_frame),
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
                "robot_model_path": self.config.robot_model_path,
                "capture_topic": self.config.capture_topic,
                "status_topic": self.config.status_topic,
            },
            "camera": {
                "open": self.camera_open,
                "depth_ready": bool(self.depth_received_at and time.monotonic()-self.depth_received_at < 1.5),
                "depth_frame": self.depth_frame_id,
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
                "samples_exists": self._saved_samples_match_board(samples) and not self.samples_dirty,
                "quality_mode": self.handeye.quality_mode,
                "samples": [
                    {"id": item["id"], "reprojection_error_px": item.get("reprojection_error_px"),
                     "captured_at": item.get("captured_at", ""), "quality_mode": item.get("quality_mode", "")}
                    for item in self.handeye.samples
                ],
                "busy": self.active_job is not None,
                "samples_path": str(samples),
                "result_path": str(samples.with_name(f"{samples.stem}_result.yaml")),
            },
            "output_dir": str(out),
            "robot_model": self._model_state(),
            "servo": self._servo_state(),
            "spatial": self._spatial_state(),
            "validation": self._validation_state(),
            "last_error": self.last_error,
        }

    def _model_state(self):
        if self.robot_model is None:
            return {"loaded": False, "error": self.robot_model_error, "links": [], "ready_for_joint_fk": False}
        data = self.robot_model.info()
        pose = self.latest_pose
        data.update(loaded=True, error='', source=self.config.robot_model_path,
                    ready_for_joint_fk=True)
        if pose:
            try:
                data['fixed_links'] = [name for name in data['links']
                    if not self.robot_model.movable_joints(pose.child_frame_id,name)]
            except ValueError:
                data['fixed_links'] = []
        return data

    def _servo_state(self):
        t=self.servo_target
        return dict(phase=self.servo_progress.get('phase','idle'),step=self.servo_progress.get('step',0),
            message=self.servo_progress.get('message',''),target=({k:v for k,v in t.items() if k!='template'} if t else None),
            history=self.servo_history[-40:], action=self.config.motion_action, group=self.config.motion_group,
            depth_ready=bool(self.depth_received_at and time.monotonic()-self.depth_received_at<1.5),
            busy=bool(self.servo_thread and self.servo_thread.is_alive()))

    def _on_depth(self, frame, stamp, frame_id):
        with self.frame_lock:
            self.depth_frame=frame
            self.depth_stamp=stamp if stamp>0 else None
            self.depth_frame_id=frame_id
            self.depth_received_at=time.monotonic()

    def _spatial_state(self):
        contact=self.spatial_contact
        if contact and (not self.robot_model or contact.get('model_path')!=self.config.robot_model_path):
            contact=None
        errors=[r['error_mm'] for r in self.spatial_measurements] if contact else []
        return dict(contact=contact, count=len(errors), measurements=self.spatial_measurements if contact else [],
                    rms_mm=float(np.sqrt(np.mean(np.square(errors)))) if errors else None,
                    max_mm=max(errors) if errors else None)

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
                    if self.spatial_overlay_enabled and self.preview_detection is not None:
                        detected=self.preview_detection
                        labels=detected.ids.ravel().tolist() if detected.ids is not None else list(range(len(detected.image_points)))
                        highlight=self.spatial_contact['corner_id'] if self.spatial_contact else -1
                        for corner,number in zip(detected.image_points.reshape(-1,2),labels):
                            px,py=[int(round(v)) for v in corner]
                            cv2.putText(display,str(number),(px+4,py-5),cv2.FONT_HERSHEY_SIMPLEX,
                                .35,(0,210,255) if number!=highlight else (0,40,255),1,cv2.LINE_AA)
                            if number==highlight:cv2.circle(display,(px,py),8,(0,40,255),2,cv2.LINE_AA)
                if self.validation_overlay_enabled and self.board_found and self.board_corners is not None:
                    try:
                        ref = load_frozen(self._validation_paths()[0])
                        latest = self.latest_pose
                        if latest is not None and self.latest_pose_at is not None and time.monotonic()-self.latest_pose_at < .4 and (
                            latest.frame_id,latest.child_frame_id,self.frame_id) == (ref['robot_base_frame'],ref['robot_end_frame'],ref['camera_frame']):
                            from calibration_engine import make_transform, quaternion_to_matrix
                            xyzquat = latest.values
                            mat = make_transform(quaternion_to_matrix(*xyzquat[3:]), xyzquat[:3])
                            from validation_engine import inv, valid_transform, _intrinsics
                            predicted_pose = inv(mat @ valid_transform(ref['handeye_transform'],'X')) @ valid_transform(ref['board_reference_in_base'],'P')
                            k,d,_ = _intrinsics(ref)
                            rvec,_ = cv2.Rodrigues(predicted_pose[:3,:3])
                            corners,_ = cv2.projectPoints(self.preview_detection.object_points,rvec,predicted_pose[:3,3],k,d)
                            for pix in corners.reshape(-1,2):
                                cv2.circle(display, tuple(np.round(pix).astype(int)), 3, (0,70,255), 1, cv2.LINE_AA)
                            cv2.putText(display, 'GREEN observed / ORANGE predicted', (12,26),
                                        cv2.FONT_HERSHEY_SIMPLEX,.55,(0,140,255),2,cv2.LINE_AA)
                    except Exception:
                        pass
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
        # TransformStamped is authoritative about both frames, so stale manually
        # entered fields from an older session cannot mislabel the calibration
        if self.config.ros_input_type != "transform" and self.config.robot_base_frame and pose.frame_id and pose.frame_id.lstrip('/') != self.config.robot_base_frame.lstrip('/'):
            self._on_ros_error("机器人基座 Frame 与收到的消息不一致")
            return
        child = pose.child_frame_id if self.config.ros_input_type == "transform" else (pose.child_frame_id or self.config.robot_end_frame)
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
            if not self.robot_model:
                raise ValueError('JointState 模式需要导入真实的机械臂 URDF，禁止使用内置示例 DH 参数')
            positions = dict(zip(joints.names,joints.values))
            transform=self.robot_model.transform(self.config.robot_base_frame,self.config.robot_end_frame,positions)
            pose_values=pose_from_matrix(transform)
            self.latest_joint_positions = positions
            self.latest_joint_received_at = time.monotonic()
            current_time=time.monotonic()
            self.pose_history.add(pose_values,current_time,joints.timestamp,joints.values,'ros_joints')
            # JointState.header.frame_id is not the robot base frame
            self.latest_pose=RosPose(pose_values,joints.timestamp,self.config.robot_base_frame,self.config.robot_end_frame)
            self.latest_pose_at=current_time
            self.latest_robot_input=joints.values
            self.latest_input_mode='ros_joints'
            self._emit('pose', {'values':list(pose_values),'timestamp':joints.timestamp,
                                'frame_id':self.config.robot_base_frame,'child_frame_id':self.config.robot_end_frame,
                                'input_mode':self.latest_input_mode,'joint_names':list(joints.names),'joints':list(joints.values)})
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
        self._ensure_no_job()
        values = asdict(self.config)
        integer_fields = {"camera_index", "camera_width", "camera_height", "chessboard_cols", "chessboard_rows", "joint_dof", "charuco_squares_x", "charuco_squares_y", "charuco_min_corners"}
        for key, value in params.items():
            if key == 'robot_model_path':
                continue  # model updates require validation through import_robot_model
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
        # Project switching restores the board geometry originally used by the destination
        # instead of interpreting its samples using the previous project's board
        if "output_dir" in params and str(values["output_dir"]) != self.config.output_dir:
            board_settings = self._project_board_settings(Path(values["output_dir"]).expanduser().resolve())
            if board_settings:
                values.update(board_settings)
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
        board_changed = bool(changed & BOARD_FIELDS)
        board_only = bool(changed) and changed <= BOARD_FIELDS
        force_switch = params.get("force_switch", False)
        if type(force_switch) is not bool:
            raise ValueError("强制切换确认必须为布尔值")
        if force_switch and (changed - {"output_dir"} - BOARD_FIELDS or "output_dir" not in changed):
            raise ValueError("强制切换只能单独用于更改项目输出目录")
        new_session = None
        if "output_dir" in changed:
            new_session = self._read_project_session(Path(candidate.output_dir).expanduser().resolve(), candidate)
        reset_captures = params.get("reset_captures", False)
        if reset_captures not in (True, False):
            raise ValueError("清空采集参数必须是布尔值")
        if reset_captures and not board_only:
            raise ValueError("仅更新棋盘参数时可以清空采集")
        if board_changed and candidate.board_type == "charuco":
            if candidate.charuco_dictionary not in available_aruco_dictionaries():
                raise ValueError("请选择当前 OpenCV 支持的 ArUco 字典")
        acquisition = {"output_dir", "camera_source", "image_topic", "camera_info_topic", "camera_frame", "robot_base_frame", "robot_end_frame", "camera_index", "camera_width", "camera_height", "chessboard_cols", "chessboard_rows", "square_size_mm", "board_type", "ros_input_type", "pose_topic", "joint_dof", "joint_names"} | {k for k in values if k.startswith("charuco_")}
        if changed & acquisition and (self.intrinsic.image_sets or self.handeye.samples):
            if not (force_switch and "output_dir" in changed and changed <= ({"output_dir"} | BOARD_FIELDS)) and not (board_only and board_changed and reset_captures):
                if 'output_dir' in changed:
                    raise ValueError(
                        '当前会话已经采集了样本，无法直接切换输出目录，以免样本和标定结果分散，'
                        '请先保存并备份当前目录中的标定成果；结束并清空当前采集会话后再切换目录'
                    )
                raise ValueError("已有采集数据，更新棋盘前需确认清空采集，不必断开机器人")
        camera_fields = {"camera_source", "image_topic", "camera_info_topic", "camera_index", "camera_width", "camera_height"}
        if self.camera_open and changed & camera_fields:
            raise ValueError("更换相机配置前请关闭相机")
        if self.ros.running and changed & {"ros_input_type", "pose_topic", "robot_base_frame", "robot_end_frame", "joint_dof", "joint_names"}:
            raise ValueError("更换位姿来源前请断开 ROS")
        # Write the old project's recoverable state before changing its path
        if "output_dir" in changed:
            self._persist_intrinsic_captures()
            if self.handeye.samples and (self.samples_dirty or not self._paths()[2].is_file()):
                self.save_samples({})
        Path(candidate.output_dir).expanduser().mkdir(parents=True, exist_ok=True)
        candidate.save(self.config_path)
        self.config = candidate
        if "output_dir" in changed:
            self.intrinsic, self.handeye, self.source_frames = new_session
            self.samples_dirty = False
            self.validation_collection = HandEyeCollection()
            self.validation_source = ""
            self.validation_reports = {'offline': None, 'live': None}
            self.validation_live_preview = None
            self.validation_overlay_enabled = False
            self.spatial_overlay_enabled = False
            self.spatial_contact = None
            self.spatial_measurements = []
            self.servo_target = None
            self.servo_history = []
            self._restore_validation_session()
        if board_changed:
            if "output_dir" not in changed:
                self._invalidate_validation()
            self.board_found, self.board_corners = False, None
            self.preview_board = None
            self.preview_detection = None
        if board_changed and reset_captures:
            self._intrinsic_capture_path().unlink(missing_ok=True)
            self.intrinsic = IntrinsicCalibration()
            self.handeye = HandEyeCollection()
            self.source_frames = None
        if changed & (acquisition - BOARD_FIELDS):
            self.board_found, self.board_corners = False, None
            with self.frame_lock:
                self.current_frame, self.frame_received_at = None, None
            self.pose_history.clear()
            self.camera_info = None
        return self._state()

    @serialized
    def update_board(self, params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_no_job()
        """Update board geometry while keeping active camera and robot subscriptions"""
        invalid = set(params) - BOARD_FIELDS - {"reset_captures"}
        if invalid:
            raise ValueError("棋盘更新只接受棋盘参数")
        return self._apply_config(params)

    def _spatial_pose(self):
        if not self.latest_pose or self.latest_pose_at is None or time.monotonic()-self.latest_pose_at>.5:
            raise ValueError('机器人位姿未连接或超过 0.5 秒未更新，请先确认机械臂已停稳')
        now=time.monotonic()
        with self.pose_history.lock:
            history=[e for e in self.pose_history.entries if now-.75<=e['received_at']<=now]
        if len(history)<3 or history[-1]['received_at']-history[0]['received_at']<.3:
            raise ValueError('请让机器人停稳至少 0.3 秒后再记录针尖接触')
        p=np.asarray([e['pose'][:3] for e in history],dtype=float)
        q=np.asarray([e['pose'][3:] for e in history],dtype=float)
        q/=np.linalg.norm(q,axis=1)[:,None]
        if np.max(np.linalg.norm(p-p[-1],axis=1))>.002 or np.max(np.rad2deg(2*np.arccos(np.clip(np.abs(q@q[-1]),0,1))))>1:
            raise ValueError('当前机械臂未停稳，暂停移动后重试')
        return history[-1]

    def _spatial_base_tool(self, values):
        from calibration_engine import make_transform, quaternion_to_matrix
        return make_transform(quaternion_to_matrix(*values[3:]),values[:3])

    @serialized
    def resolve_tool_link(self, params):
        if not self.robot_model:
            raise ValueError('请先在机器人接口中导入包含工具 Link 的 URDF')
        pose=self.latest_pose
        if not pose or not self.latest_pose_at or time.monotonic()-self.latest_pose_at>.5:
            raise ValueError('尚未收到新鲜的末端位姿')
        target=str(params.get('link','')).strip()
        if not target:
            raise ValueError('请选择目标工具 Link')
        fixed=self.robot_model.transform(pose.child_frame_id,target,only_fixed=True)
        mat=self._spatial_base_tool(pose.values)@fixed
        return dict(link=target,frame=pose.frame_id,source_link=pose.child_frame_id,
                    position_m=mat[:3,3].tolist(),transform=mat.tolist(),stamp=pose.timestamp)

    @serialized
    def record_spatial_contact(self, params):
        self._ensure_no_job()
        from validation_engine import load_frozen
        if not self.robot_model:
            raise ValueError('请先导入真实的 URDF，确认针尖 Link 的原点与实际针尖重合')
        fixed=load_frozen(self._validation_paths()[0])
        if self.latest_pose is None:
            raise ValueError('请先连接机械臂并等待位姿')
        if (self.latest_pose.frame_id,self.latest_pose.child_frame_id)!=(fixed['robot_base_frame'],fixed['robot_end_frame']):
            raise ValueError('当前机械臂的 Base / End Frame 与求解矩阵不匹配')
        link=str(params.get('link','')).strip()
        if not link:raise ValueError('请选择接触目标 Link')
        index=int(params.get('corner_id',-1))
        if fixed['board']!=self.config.board_config():
            raise ValueError('标定板参数已变化，请恢复求解时使用的棋盘')
        board=CalibrationBoard(self.config.board_config())
        count=len(board.object_points)
        if index<0 or index>=count:raise ValueError(f'标定板角点 ID 超出范围，应为 0 到 {count-1}')
        transform=self.robot_model.transform(self.latest_pose.child_frame_id,link,only_fixed=True)
        entry=self._spatial_pose()
        world=self._spatial_base_tool(entry['pose'])@transform
        reference=world[:3,3].tolist()
        import hashlib
        source_path=Path(self.config.robot_model_path)
        model_digest=hashlib.sha256(source_path.read_bytes()).hexdigest()
        frozen_path=self._validation_paths()[0]
        solution_digest=hashlib.sha256(frozen_path.read_bytes()).hexdigest()
        record=dict(base_frame=fixed['robot_base_frame'],end_frame=fixed['robot_end_frame'],
                    camera_frame=fixed['camera_frame'],link=link,corner_id=index,
                    point_m=reference,source_pose_stamp=entry['robot_timestamp'],
                    model_path=str(source_path),model_sha256=model_digest,
                    frozen_sha256=solution_digest,created_at=time.time(),
                    reference_type='robot_fk_tool_contact',units='m')
        self.spatial_contact=record
        self.spatial_measurements=[]
        out,_,_=self._paths()
        (out/'spatial_contact.yaml').write_text(yaml.safe_dump(record,sort_keys=False,allow_unicode=True),encoding='utf-8')
        (out/'spatial_validation_report.yaml').unlink(missing_ok=True)
        self._emit_state()
        return record

    @serialized
    def measure_spatial_target(self, _params):
        self._ensure_no_job()
        from calibration_engine import load_intrinsics, make_transform
        from calibration_board import solve_board_pose
        from validation_engine import load_frozen, valid_transform
        from hashlib import sha256
        ref=self.spatial_contact
        if not ref:
            raise ValueError('请先用针尖接触已知角点，记录参考点')
        if sha256(Path(ref['model_path']).read_bytes()).hexdigest()!=ref['model_sha256']:
            raise ValueError('URDF 已变化，请重新建立针尖参考')
        frozen_path=self._validation_paths()[0]
        if sha256(frozen_path.read_bytes()).hexdigest()!=ref['frozen_sha256']:
            raise ValueError('手眼矩阵已变化，请重新建立针尖参考')
        frozen=load_frozen(frozen_path)
        if (ref['base_frame'],ref['end_frame'],ref['camera_frame']) != (
                frozen['robot_base_frame'], frozen['robot_end_frame'], frozen['camera_frame']):
            raise ValueError('参考点坐标系与已冻结结果不一致')
        with self.frame_lock:
            frame=self.current_frame.copy() if self.current_frame is not None else None
            receipt=self.frame_received_at
            frame_stamp=self.frame_ros_stamp
            image_frame=self.frame_id
        if frame is None or receipt is None or time.monotonic()-receipt>.5:
            raise ValueError('相机帧已过期，请等待实时画面')
        if image_frame!=ref['camera_frame']:
            raise ValueError('RGB 图像光学 Frame 与求解矩阵不一致')
        entry,dt=self.pose_history.match(receipt,time.monotonic())
        if frame_stamp is not None and entry['robot_timestamp'] is not None:
            d=abs(float(frame_stamp)-float(entry['robot_timestamp']))
            if d<1 and d>.1:
                raise ValueError('图像与末端位姿时间戳差过大')
        robot=self._spatial_base_tool(entry['pose'])
        _,intrinsics,_=self._paths()
        k,d,metadata=load_intrinsics(intrinsics)
        from validation_engine import _intrinsics
        expected_k,expected_d,expected_size=_intrinsics(frozen)
        diagnostics = self._spatial_camera_diagnostics()
        if not diagnostics["ok"]:
            raise ValueError("针尖测量相机配置不一致：" + "；".join(diagnostics["problems"]) +
                             f"；RGB 来源：{diagnostics['image_topic']}；内参文件：{diagnostics['intrinsics_path']}")
        detector=CalibrationBoard(self.config.board_config())
        observation=detector.detect(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),k,d)
        target_to_camera,error=solve_board_pose(observation.object_points,observation.image_points,k,d)
        ids=observation.ids.ravel().astype(int).tolist() if observation.ids is not None else list(range(len(observation.object_points)))
        if ref['corner_id'] not in ids:
            raise ValueError(f'当前图像未识别到参考角点 ID {ref["corner_id"]}，请换一个视角')
        selected=ids.index(ref['corner_id'])
        point_board=np.r_[observation.object_points[selected],1.]
        handeye=valid_transform(frozen['handeye_transform'],'handeye_transform')
        predicted=robot@handeye@target_to_camera@point_board
        diff=predicted[:3]-np.asarray(ref['point_m'],dtype=float)
        row=dict(id=len(self.spatial_measurements)+1,corner_id=ref['corner_id'],
                 vision_point_m=predicted[:3].tolist(),reference_point_m=ref['point_m'],
                 error_xyz_mm=(diff*1000).tolist(),error_mm=float(np.linalg.norm(diff)*1000),
                 board_pnp_reprojection_px=float(error),pose_image_dt_ms=float(dt),
                 robot_pose_stamp=entry['robot_timestamp'],image_stamp=frame_stamp,
                 acquired_at=time.time())
        self.spatial_measurements.append(row)
        errors=[item['error_mm'] for item in self.spatial_measurements]
        out,_,_=self._paths()
        payload=dict(reference=ref,measurement_method='known_board_corner_PnP',
            note='机器人 FK 针尖接触作为参考，不是独立计量真值；报告包含模型/TCP/相机/手眼/接触误差',
            count=len(errors),rms_mm=float(np.sqrt(np.mean(np.square(errors)))),
            p95_mm=float(np.percentile(errors,95)),max_mm=float(max(errors)),
            samples=self.spatial_measurements)
        (out/'spatial_validation_report.yaml').write_text(
            yaml.safe_dump(payload,sort_keys=False,allow_unicode=True),encoding='utf-8')
        self._emit_state()
        return row

    @serialized
    def clear_spatial(self, _params):
        self.spatial_contact=None
        self.spatial_measurements=[]
        self._emit_state()
        return {'ok':True}

    @serialized
    def import_robot_model(self, params: dict[str, Any]):
        self._ensure_no_job()
        if self.ros.running:
            raise ValueError('更换机器人模型前请断开机械臂连接')
        if self.handeye.samples and self.config.ros_input_type=='joints':
            raise ValueError('当前用 JointState 正运动学采集了样本，更换 URDF 前需先备份并清空样本')
        path=str(params.get('path','')).strip()
        if not path:
            raise ValueError('请选择 Description 文件夹、ZIP、URDF 或 Xacro')
        import shutil
        staged, relative, model = stage_description(path, self.data_dir)
        destination = self.data_dir / 'robot_description'
        previous = self.data_dir / '.robot_description_previous'
        previous.exists() and shutil.rmtree(previous)
        try:
            if destination.exists():
                destination.rename(previous)
            staged.rename(destination)
            model_file = destination / relative
            # Installation remains usable after source archive is deleted
            self.config.robot_model_path = str(model_file)
            self.config.save(self.config_path)
        except Exception:
            if destination.exists() and destination != staged:
                shutil.rmtree(destination, ignore_errors=True)
            if previous.exists():
                previous.rename(destination)
            raise
        finally:
            if staged.exists():
                shutil.rmtree(staged, ignore_errors=True)
        if previous.exists():
            shutil.rmtree(previous, ignore_errors=True)
        self.robot_model=model
        self.robot_model_error=''
        self.spatial_contact=None
        self.spatial_measurements=[]
        self._emit_state()
        return self._model_state()

    @serialized
    def get_model_preview(self, _params):
        if self.robot_model is None or not self.config.robot_model_path:
            raise ValueError('先导入 Description，才能查看三维机械臂')
        model_path = Path(self.config.robot_model_path)
        if not model_path.is_file():
            raise ValueError('机器人模型文件已被移动，请重新导入 Description')
        live = bool(self.latest_joint_received_at is not None and
                    time.monotonic() - self.latest_joint_received_at < 2 and
                    self.config.ros_input_type == 'joints' and self.ros.running)
        positions = self.latest_joint_positions if live else {}
        preview = preview_payload(model_path, self.robot_model, positions)
        preview['state_source'] = ('live_joint_state' if preview['model_pose']=='joint_state' else 'model_reference')
        preview['frames_note'] = ('当前关节状态' if preview['model_pose']=='joint_state' else 'URDF 零位示意，未获得完整关节角，不能代表实际整臂姿态')
        preview['active_pose'] = self._state().get('ros',{}).get('pose')
        # Render the calibrated camera only when solution matches the current samples
        try:
            import yaml
            from calibration_engine import make_transform, quaternion_to_matrix
            _,_,sample_path = self._paths()
            result_path = sample_path.with_name(sample_path.stem+'_result.yaml')
            if (self.latest_pose and self.latest_pose_at and time.monotonic()-self.latest_pose_at<1.5 and sample_path.is_file() and result_path.is_file()
                    and result_path.stat().st_mtime_ns >= sample_path.stat().st_mtime_ns):
                result = yaml.safe_load(result_path.read_text(encoding='utf-8')) or {}
                parent = result.get('parent_frame')
                if parent == self.latest_pose.child_frame_id:
                    x = np.asarray(result.get('transform_matrix'), dtype=float)
                    if x.shape == (4,4) and np.isfinite(x).all():
                        values = self.latest_pose.values
                        base_tool = make_transform(quaternion_to_matrix(*values[3:]), values[:3])
                        root_base = self.robot_model.transform(self.robot_model.root, self.latest_pose.frame_id,
                            self.latest_joint_positions if live else {n:0.0 for n,j in self.robot_model.joints.items() if j['kind']!='fixed'})
                        preview['camera_frame'] = {'name':result.get('child_frame','camera'),
                            'parent':self.latest_pose.frame_id, 'transform':(root_base@base_tool@x).round(8).tolist()}
                        if self.handeye.samples:
                            # Last capture is a historical observation, not a live board tracker
                            observation = self.handeye.samples[-1]
                            if ('gripper_in_base' in observation and 'target_to_camera' in observation):
                                board = (np.asarray(observation['gripper_in_base'])@x@
                                         np.asarray(observation['target_to_camera']))
                                preview['board_frame'] = {'name':'board (history)',
                                    'parent':self.latest_pose.frame_id,
                                    'transform':(root_base@board).round(8).tolist(), 'historical':True}
        except Exception:
            pass
        return preview

    @serialized
    def import_ros_model(self, _params):
        if self.ros.running or (self.handeye.samples and self.config.ros_input_type=='joints'):
            raise ValueError('请断开机械臂连接；JointState 模式已有采样数据时还需备份并清空样本')
        try:
            import rclpy
            from rclpy.node import Node
            from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
            from std_msgs.msg import String
        except ImportError as exc:
            raise ValueError('未加载 ROS2 Python 环境，无法读取 /robot_description') from exc
        created=not rclpy.ok()
        if created:rclpy.init(args=None)
        node=rclpy.create_node('handeye_robot_description_reader')
        values=[]
        try:
            qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,
                           reliability=ReliabilityPolicy.RELIABLE)
            node.create_subscription(String,'/robot_description',lambda msg:values.append(msg.data),qos)
            start=time.monotonic()
            while not values and time.monotonic()-start<3.0:
                rclpy.spin_once(node,timeout_sec=0.15)
        finally:
            node.destroy_node()
            if created:rclpy.shutdown()
        if not values:
            raise ValueError('3 秒内未收到 /robot_description，请先启动 robot_state_publisher 或改为导入 URDF 文件')
        # Isolate the downloaded XML rather than copying every URDF in /tmp
        import tempfile
        with tempfile.TemporaryDirectory(prefix='handeye-ros-model-',dir=self.data_dir) as directory:
            temporary=Path(directory)/'robot.urdf'
            temporary.write_text(values[-1],encoding='utf-8')
            return self.import_robot_model({'path':str(temporary)})

    @serialized
    def clear_robot_model(self, _params):
        if self.ros.running:
            raise ValueError('移除模型前请先断开机械臂')
        if self.config.ros_input_type=='joints':
            raise ValueError('JointState 模式必须保留 URDF，请先切换位姿输入类型')
        self.robot_model=None
        self.robot_model_error=''
        self.config.robot_model_path=''
        self.config.save(self.config_path)
        self.spatial_contact=None
        self.spatial_measurements=[]
        self._emit_state()
        return self._model_state()

    @serialized
    def connect_robot(self, _params: dict[str, Any]) -> dict[str, Any]:
        """Connect the selected pose source and camera together, with rollback"""
        c = self.config
        expected = {
            "pose": "geometry_msgs/msg/PoseStamped",
            "transform": "geometry_msgs/msg/TransformStamped",
            "joints": "sensor_msgs/msg/JointState",
        }
        if self.servo_thread and self.servo_thread.is_alive():
            raise ValueError("运动期间不能重连机器人，请先取消并确认机械臂停止")
        if c.camera_source == "ros" and not c.image_topic.strip():
            raise ValueError("请选择相机 Image 话题")
        if c.ros_input_type != "tf" and not c.pose_topic.strip():
            raise ValueError("请选择机械臂位姿话题")
        if c.ros_input_type == "pose" and not c.robot_end_frame:
            raise ValueError("PoseStamped 不携带末端 Frame，请填写末端 Frame")
        if c.ros_input_type in ("tf", "joints") and (not c.robot_base_frame or not c.robot_end_frame):
            raise ValueError("请填写基座 Frame 与末端 Frame")
        if c.ros_input_type == 'joints':
            if not self.robot_model:
                raise ValueError('JointState 模式必须先导入有效的 URDF 模型')
            self.robot_model.transform(c.robot_base_frame,c.robot_end_frame,{
                name:0.0 for name in self.robot_model.joints})
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
        self._cancel_servo_internal()
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
        self._cancel_servo_internal()
        self.ros_depth.stop()
        self.depth_frame = None
        self.depth_stamp = None
        self.depth_received_at = None
        self.depth_frame_id = ""
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
        self._intrinsic_capture_path().unlink(missing_ok=True)
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
            if not self.robot_model:
                raise ValueError('关节角手动输入必须先导入真实 URDF')
            names=[x.strip() for x in self.config.joint_names.split(',') if x.strip()]
            if not names or len(names)!=len(joints):
                raise ValueError('手动关节角输入须按 URDF 关节名称配置映射，数量必须一致')
            transform=self.robot_model.transform(self.config.robot_base_frame,self.config.robot_end_frame,dict(zip(names,joints)))
            return pose_from_matrix(transform), joints, 'joints' 
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
        self._ensure_no_job()
        result = self.handeye.add(
            frame, pose, intrinsics,
            self.config.chessboard_cols, self.config.chessboard_rows,
            self.config.square_size_mm, input_mode, timestamp,
            robot_pose_input=robot_input, quality_mode=quality, board=self.config.board_config(),
        )
        self.samples_dirty = True
        self._invalidate_validation()
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
        self._ensure_no_job()
        self.handeye = HandEyeCollection()
        self.source_frames = None
        _, _, saved_path = self._paths()
        if saved_path.exists():
            shutil.copy2(saved_path, saved_path.with_name("samples.backup.yaml"))
            saved_path.unlink()
        self.samples_dirty = False
        self._invalidate_result()
        self._emit_state()
        return {"count": 0}

    @serialized
    def save_samples(self, _params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_no_job()
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
        temp = samples.with_name(samples.name + ".pending")
        try:
            temp.write_text(yaml.safe_dump(document, sort_keys=False, allow_unicode=True), encoding="utf-8")
            temp.replace(samples)
        finally:
            temp.unlink(missing_ok=True)
        self.samples_dirty = False
        self._invalidate_result()
        self.ros.publish_status("samples_saved", path=str(samples), count=len(self.handeye.samples))
        self._emit_state()
        return {"path": str(samples), "count": len(self.handeye.samples)}

    def _ensure_no_job(self) -> None:
        if self.active_job is not None:
            raise RuntimeError("请先等待当前计算完成或取消当前操作")

    def _invalidate_result(self) -> None:
        _, _, samples = self._paths()
        # Old solutions must never be exported after a sample is deleted or imported
        for name in (f"{samples.stem}_result.yaml", "handeye_transform.yaml"):
            (samples.parent / name).unlink(missing_ok=True)
        self._invalidate_validation()

    @serialized
    def import_samples(self, params: dict[str, Any]) -> dict[str, Any]:
        """Restore a collection with its frozen board, intrinsics, frames and stable IDs"""
        self._ensure_no_job()
        if self.handeye.samples and not params.get("replace", False):
            raise ValueError("当前会话已有样本，请先确认替换")
        source = Path(str(params.get("path", ""))).expanduser().resolve()
        if not source.is_file() or source.suffix.lower() not in (".yaml", ".yml"):
            raise ValueError("请选择有效的 samples.yaml 文件")
        import yaml
        from calibration_engine import load_intrinsics, intrinsic_binding
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("handeye_mode") != "eye_in_hand":
            raise ValueError("文件不是 Eye-in-Hand 样本数据")
        board = self.config.board_config()
        if data.get("board") != board:
            if not (self.config.board_type == "chessboard" and not data.get("board") and
                    data.get("chessboard") == f"{self.config.chessboard_cols}x{self.config.chessboard_rows}" and
                    float(data.get("square_size_mm", -1)) == self.config.square_size_mm):
                raise ValueError("样本标定板与当前配置不同，请先更新标定板参数")
        base, end, camera = (str(data.get(k) or "").strip() for k in
                             ("robot_base_frame", "robot_end_frame", "camera_frame"))
        if not base or not end or not camera or base == end:
            raise ValueError("样本缺少可靠的基座、末端或相机坐标系，不允许猜测 Frame")
        if self.latest_pose is not None:
            if (base, end) != (self.latest_pose.frame_id, self.latest_pose.child_frame_id):
                raise ValueError("导入样本的机器人 Frame 与当前在线机械臂不一致")
        with self.frame_lock:
            frame_id = self.frame_id
        if frame_id and camera != frame_id:
            raise ValueError("导入样本的相机 Frame 与当前图像话题不一致")
        entries = data.get("samples")
        if not isinstance(entries, list) or not entries:
            raise ValueError("文件缺少有效样本")
        if len(entries) > 10000:
            raise ValueError("样本数量超出限制")
        quality = data.get("collection_quality_mode") or entries[0].get("quality_mode") or "standard"
        if quality not in ("minimal", "standard", "strict"):
            raise ValueError("样本质量模式无法识别")
        prepared, ids = [], set()
        for number, entry in enumerate(entries, 1):
            if not isinstance(entry, dict):
                raise ValueError(f"样本 {number} 格式错误")
            sid = entry.get("id", number)
            if type(sid) is not int or sid <= 0 or sid in ids:
                raise ValueError(f"样本 ID 无效或重复：{sid}")
            ids.add(sid)
            for key in ("gripper_in_base", "target_to_camera"):
                matrix = np.asarray(entry.get(key), dtype=np.float64)
                if (matrix.shape != (4, 4) or not np.isfinite(matrix).all()
                    or not np.allclose(matrix[3], [0, 0, 0, 1], atol=1e-5)
                    or not np.allclose(matrix[:3, :3].T @ matrix[:3, :3], np.eye(3), atol=1e-2)
                    or abs(float(np.linalg.det(matrix[:3, :3])) - 1) > 1e-2):
                    raise ValueError(f"样本 #{sid} 的 {key} 不是有效刚体变换")
            if entry.get("quality_mode", quality) != quality:
                raise ValueError("导入样本包含不一致的质量模式")
            for key, expected in zip(("robot_base_frame", "robot_end_frame", "camera_frame"), (base, end, camera)):
                if entry.get(key) and entry[key] != expected:
                    raise ValueError(f"样本 #{sid} 的 Frame 与文件头不一致")
            entry = dict(entry)
            entry["id"] = sid
            entry["quality_mode"] = quality
            entry.update(robot_base_frame=base, robot_end_frame=end, camera_frame=camera)
            prepared.append(entry)

        out, intrinsic_path, target = self._paths()
        captured_K = data.get("camera_matrix_at_collection")
        captured_D = data.get("distortion_at_collection")
        captured_size = data.get("image_size_at_collection")
        if not captured_K or not captured_D or not captured_size or len(captured_size) != 2:
            raise ValueError("样本缺少采集时冻结的相机内参，不能安全追加")
        expected = dict(camera_matrix=captured_K, distortion_coefficients=captured_D,
                        image_width=int(captured_size[0]), image_height=int(captured_size[1]),
                        created_at=data.get("intrinsics_created_at"))
        frozen = intrinsic_binding(expected)
        if intrinsic_path.is_file():
            _, _, current = load_intrinsics(intrinsic_path)
            live = intrinsic_binding(current)
            if not (np.allclose(live["camera_matrix"], frozen["camera_matrix"], atol=1e-9, rtol=0)
                    and np.allclose(live["distortion"], frozen["distortion"], atol=1e-9, rtol=0)
                    and live["image_size"] == frozen["image_size"]):
                raise ValueError("样本冻结的相机内参与当前内参文件不一致")
        else:
            intrinsic_path.parent.mkdir(parents=True, exist_ok=True)
            intrinsic_path.write_text(yaml.safe_dump(expected, sort_keys=False, allow_unicode=True), encoding="utf-8")
            current = expected

        collection = HandEyeCollection()
        collection.samples = prepared
        collection.quality_mode = quality
        collection.board_spec = dict(board)
        collection.binding = intrinsic_binding(current)
        collection.intrinsics_snapshot = current
        self.handeye = collection
        self.source_frames = (base, end, camera)
        self.samples_dirty = True
        if target.exists() and target != source:
            shutil.copy2(target, target.with_name("samples.backup.yaml"))
        # Write the imported collection through the normal serialization path
        saved = self.save_samples({})
        return {"path": saved["path"], "count": len(prepared), "quality_mode": quality}

    @serialized
    def delete_samples(self, params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_no_job()
        selected = params.get("ids", [])
        if not isinstance(selected, list) or not selected:
            raise ValueError("请至少选择一个样本 ID")
        try:
            ids = {int(sid) for sid in selected}
        except (ValueError, TypeError) as exc:
            raise ValueError("样本 ID 必须是整数") from exc
        known = {int(s["id"]) for s in self.handeye.samples}
        if not ids <= known or len(ids) != len(selected):
            raise ValueError("样本 ID 不存在或包含重复项")
        _, _, current_path = self._paths()
        if current_path.is_file():
            shutil.copy2(current_path, current_path.with_name("samples.backup.yaml"))
        self.handeye.samples = [s for s in self.handeye.samples if s["id"] not in ids]
        self._invalidate_result()
        if self.handeye.samples:
            self.samples_dirty = True
            self.save_samples({})
        else:
            self.handeye = HandEyeCollection()
            self.source_frames = None
            _, _, path = self._paths()
            path.unlink(missing_ok=True)
            self.samples_dirty = False
        self._emit_state()
        return {"deleted": sorted(ids), "count": len(self.handeye.samples)}

    @serialized
    def freeze_validation(self, _params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_no_job()
        out, _, samples = self._paths()
        if self.samples_dirty or not self._saved_samples_match_board(samples):
            raise ValueError('请先保存训练样本')
        result = out / 'samples_result.yaml'
        if not result.exists() or result.stat().st_mtime_ns < samples.stat().st_mtime_ns:
            raise ValueError('求解结果缺失或已经过期，请先重新求解')
        ref, live, report = self._validation_paths()
        fixed = freeze_solution(samples, result, ref)
        report.unlink(missing_ok=True)
        for mode in ('offline','live'):
            self._validation_report_path(mode).unlink(missing_ok=True)
        if live.exists():
            shutil.copy2(live, live.with_name('validation_samples.backup.yaml'))
            live.unlink()
        self.validation_collection = HandEyeCollection()
        self.validation_reports = {'offline':None,'live':None}
        self.validation_live_preview = None
        self.validation_source = ''
        self.validation_overlay_enabled = False
        self._emit_state()
        return {'path': str(ref), 'frames': [fixed['robot_end_frame'], fixed['camera_frame']]}

    @serialized
    def import_validation(self, params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_no_job()
        ref, _, report = self._validation_paths()
        fixed = load_frozen(ref)
        path = Path(str(params.get('path',''))).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() not in ('.yaml','.yml'):
            raise ValueError('请选择独立验证 samples.yaml')
        if path.resolve() == Path(fixed['training_sample_path']).resolve():
            raise ValueError('不能把训练样本作为独立验证样本')
        doc = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        validate_metadata(fixed, doc)
        signatures = [sample_signature(s) for s in doc.get('samples',[])]
        if not signatures or any(sig in fixed['training_sample_signatures'] for sig in signatures):
            raise ValueError('验证数据为空或与训练样本重叠')
        if len(set(signatures)) != len(signatures):
            raise ValueError('验证数据存在重复样本')
        self.validation_source = str(path)
        self._validation_report_path('offline').unlink(missing_ok=True)
        self.validation_reports['offline'] = None
        if report.is_file(): report.unlink()
        self._emit_state()
        return {'path': str(path), 'count': len(signatures)}

    @serialized
    def set_validation_overlay(self, params: dict[str, Any]) -> dict[str, Any]:
        self.validation_overlay_enabled = bool(params.get('enabled',False))
        self.spatial_overlay_enabled = bool(params.get('spatial',False))
        return {'enabled': self.validation_overlay_enabled,'spatial':self.spatial_overlay_enabled}

    @serialized
    def capture_validation(self, _params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_no_job()
        ref, live_file, report = self._validation_paths()
        fixed = load_frozen(ref)
        with self.frame_lock:
            frame = self.current_frame.copy() if self.current_frame is not None else None
            frame_time = self.frame_received_at
            frame_stamp = self.frame_ros_stamp
            image_frame = self.frame_id
        if frame is None or frame_time is None or time.monotonic()-frame_time > .5:
            raise ValueError('相机图像未连接或已经过期')
        if self.latest_pose is None:
            raise ValueError('尚未收到机器人末端位姿')
        entry, sync_dt = self.pose_history.match(frame_time, time.monotonic())
        pose = entry['pose']
        robot_input = entry['robot_input'] or pose
        timestamp = entry['robot_timestamp']
        if (self.latest_pose.frame_id,self.latest_pose.child_frame_id,image_frame) != (
                fixed['robot_base_frame'],fixed['robot_end_frame'],fixed['camera_frame']):
            raise ValueError('在线机器人或相机 Frame 与冻结矩阵不一致')
        if frame_stamp is not None and timestamp is not None and abs(frame_stamp-timestamp) < 1 and abs(frame_stamp-timestamp) > .1:
            raise ValueError('ROS2 图像与机器人位姿时间戳差异过大')
        _, intrinsic_path, _ = self._paths()
        if not intrinsic_path.is_file():
            raise ValueError('缺少当前相机内参')
        sample = self.validation_collection
        captured = sample.add(frame, pose, intrinsic_path,
             self.config.chessboard_cols,self.config.chessboard_rows,self.config.square_size_mm,
             entry['input_mode'], timestamp, robot_pose_input=robot_input,
             quality_mode='minimal',board=self.config.board_config())
        new = sample.samples[-1]
        new['id'] = max([int(s['id']) for s in sample.samples[:-1]], default=0) + 1
        new.update(robot_base_frame=fixed['robot_base_frame'], robot_end_frame=fixed['robot_end_frame'],
                   camera_frame=fixed['camera_frame'], sync_frame_pose_dt_ms=sync_dt)
        signature = sample_signature(new)
        if signature in fixed['training_sample_signatures'] or any(
                signature == sample_signature(old) for old in sample.samples[:-1]):
            sample.samples.pop()
            raise ValueError('验证样本与训练数据或当前会话重复，请改变机械臂姿态')
        # Commit the capture only after validation of geometry and independence
        pending = live_file.with_suffix('.pending.yaml')
        try:
            sample.save(pending, intrinsic_path, self.config.chessboard_cols,
                        self.config.chessboard_rows,self.config.square_size_mm,board=self.config.board_config())
            doc = yaml.safe_load(pending.read_text(encoding='utf-8')) or {}
            doc.update(robot_base_frame=fixed['robot_base_frame'], robot_end_frame=fixed['robot_end_frame'], camera_frame=fixed['camera_frame'])
            row = evaluate_sample(fixed,new,doc)
            preview = evaluate_dataset(fixed,doc,mode='live')
            pending.write_text(yaml.safe_dump(doc,sort_keys=False,allow_unicode=True),encoding='utf-8')
            pending.replace(live_file)
        except Exception:
            sample.samples.pop()
            raise
        finally:
            pending.unlink(missing_ok=True)
        self.validation_live_preview = preview
        self._validation_report_path('live').unlink(missing_ok=True)
        self.validation_reports['live'] = None
        if report.is_file(): report.unlink()
        self._emit_state()
        return {'count':len(sample.samples),'sample':row}

    @serialized
    def clear_validation(self, _params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_no_job()
        _, live, report = self._validation_paths()
        self.validation_collection = HandEyeCollection()
        self.validation_reports['live'] = None
        self.validation_live_preview = None
        live.unlink(missing_ok=True)
        self._validation_report_path('live').unlink(missing_ok=True)
        if report.is_file(): report.unlink()
        self._emit_state()
        return {'count':0}

    @serialized
    def export_validation(self, _params: dict[str, Any]) -> dict[str, Any]:
        mode = str(_params.get('mode','offline'))
        if mode not in ('offline','live'): raise ValueError('验证模式无效')
        report_path = self._validation_report_path(mode)
        fixed = load_frozen(self._validation_paths()[0])
        if not report_path.is_file():
            raise ValueError('请先完成离线或真机验证')
        report = yaml.safe_load(report_path.read_text(encoding='utf-8')) or {}
        if report.get('fixed_reference_sha256') != digest(fixed):
            raise ValueError('验证报告已经失效')
        return {'path': str(report_path)}

    @serialized
    def start_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_no_job()
        name = str(params.get("name", "solve"))
        mode = str(params.get("solve_mode", "robust"))
        if name not in ("diagnose", "solve", "intrinsic", "validate_offline", "validate_live"):
            raise ValueError("不支持的计算操作")
        if name in ('validate_offline', 'validate_live'):
            ref, live, _ = self._validation_paths()
            load_frozen(ref)
            validation_path = Path(self.validation_source) if name == 'validate_offline' else live
            if not validation_path.is_file():
                raise ValueError('请先导入独立验证样本或采集真机验证样本')
        if name == "intrinsic":
            if self.handeye.samples:
                raise ValueError("已有外参样本，重新标定内参前请先清空外参样本")
            quality = str(params.get("quality_mode", "standard"))
            minimums = {"minimal": 3, "standard": 10, "strict": 15}
            if quality not in minimums or len(self.intrinsic.image_sets) < minimums[quality]:
                raise ValueError("内参采集数量未达到当前质量模式的要求")
            if self.intrinsic.quality_mode != quality:
                raise ValueError("内参采样质量模式不一致")
        elif name not in ("validate_offline", "validate_live"):
            _, _, samples = self._paths()
            if self.samples_dirty or not self._saved_samples_match_board(samples):
                raise ValueError("请先保存当前样本，再开始诊断或求解")
            result_path = samples.with_name(f"{samples.stem}_result.yaml")
            if name == "verify" and (not result_path.exists() or
                    result_path.stat().st_mtime_ns < samples.stat().st_mtime_ns):
                raise ValueError("请先对当前采集数据重新求解，再进行验证")
        job = {"id": uuid.uuid4().hex, "name": name, "cancelled": False, "process": None}
        self.active_job = job
        worker = threading.Thread(target=self._run_job, args=(job, mode, params), daemon=True, name="calibration-job")
        worker.start()
        self._emit_state()
        return {"id": job["id"], "name": name}

    def _run_job(self, job: dict, mode: str, params: dict) -> None:
        import yaml
        logs = []
        result = None
        code = 1
        try:
            with tempfile.TemporaryDirectory(prefix="handeye_job_") as work:
                work = Path(work)
                _, intrinsics, samples = self._paths()
                command = [sys.executable, "-u", str(ROOT / "algorithm_runner.py"),
                           "--job", job["name"], "--mode", mode]
                if job['name'] in ('validate_offline','validate_live'):
                    ref, live, _ = self._validation_paths()
                    source = Path(self.validation_source) if job['name'] == 'validate_offline' else live
                    command = [sys.executable, '-u', str(ROOT / 'validation_engine.py'),
                               '--reference', str(ref), '--samples', str(source),
                               '--report', str(work / 'validation_report.yaml'),
                               '--mode', 'offline' if job['name'] == 'validate_offline' else 'live']
                    if params.get('thresholds'):
                        command += ['--thresholds', json.dumps(params['thresholds'])]
                elif job["name"] == "intrinsic":
                    snapshot = work / "intrinsic.pkl"
                    target = work / "camera_intrinsics.yaml"
                    with self.session_lock:
                        with snapshot.open("wb") as handle:
                            pickle.dump(self.intrinsic, handle, protocol=pickle.HIGHEST_PROTOCOL)
                    command += ["--snapshot", str(snapshot), "--output", str(target),
                                "--quality", str(params.get("quality_mode", "standard")),
                                "--board", json.dumps(self.config.board_config(), ensure_ascii=False)]
                else:
                    # Isolate algorithm output until successful completion so cancellation
                    # cannot overwrite a validated solution
                    shadow = work / "samples.yaml"
                    shutil.copy2(samples, shadow)
                    if intrinsics.is_file():
                        shutil.copy2(intrinsics, work / "camera_intrinsics.yaml")
                    result_file = samples.with_name(f"{samples.stem}_result.yaml")
                    if job["name"] == "verify" and result_file.is_file():
                        shutil.copy2(result_file, work / "samples_result.yaml")
                    command += ["--samples", str(shadow)]
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           text=True, bufsize=1, cwd=str(ROOT))
                with self.session_lock:
                    job["process"] = process
                    if job["cancelled"]:
                        process.terminate()
                for line in process.stdout:
                    if line.startswith("HANDEYE_JOB_RESULT:"):
                        result = json.loads(line.split(":", 1)[1])
                    else:
                        logs.append(line)
                        self._emit("log", {"text": line})
                code = process.wait()
                with self.session_lock:
                    if job["cancelled"]:
                        code = 130
                    if code == 0 and job["name"] == "intrinsic":
                        if not target.is_file():
                            code = 1
                        else:
                            target.replace(intrinsics)
                            self.intrinsic = IntrinsicCalibration()
                    if code == 0 and job['name'] in ('validate_offline','validate_live'):
                        produced = work / 'validation_report.yaml'
                        if not produced.is_file():
                            code = 1
                        else:
                            _, _, report_path = self._validation_paths()
                            mode = 'offline' if job['name'] == 'validate_offline' else 'live'
                            produced.replace(self._validation_report_path(mode))
                            shutil.copy2(self._validation_report_path(mode), report_path)
                            result = yaml.safe_load(report_path.read_text(encoding='utf-8'))
                            self.validation_reports[mode] = result
                            result = self._compact_validation_report(result)
                    if code == 0 and job["name"] == "solve":
                        produced = work / "samples_result.yaml"
                        if not produced.is_file():
                            code = 1
                        else:
                            produced.replace(result_file)
                            self._invalidate_validation()
                            result = yaml.safe_load(result_file.read_text(encoding="utf-8"))
        except Exception as exc:
            code = 1
            logs.append(f"计算错误：{exc}\n")
            self._emit("log", {"text": logs[-1]})
        finally:
            with self.session_lock:
                if self.active_job is job:
                    self.active_job = None
            self._emit("tool_done", {"id": job["id"], "name": job["name"], "ok": code == 0,
                                      "cancelled": bool(job["cancelled"]), "exit_code": code,
                                      "result": result, "log": "".join(logs)})
            self._emit_state()

    @serialized
    def cancel_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        job = self.active_job
        if not job or job["id"] != str(params.get("id", "")):
            return {"cancelled": False}
        job["cancelled"] = True
        proc = job.get("process")
        if proc is not None and proc.poll() is None:
            proc.terminate()
            def ensure_stopped():
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
            threading.Thread(target=ensure_stopped, daemon=True).start()
        return {"cancelled": True}

    @serialized
    def run_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        name = str(params.get("name", "solve"))
        if name not in ('diagnose','solve'):
            raise ValueError('独立验证请使用验证页面，不允许旧的训练样本内验证')
        mode = str(params.get("solve_mode", "robust"))
        _, _, samples = self._paths()
        if not self._saved_samples_match_board(samples):
            raise FileNotFoundError("没有与当前棋盘参数匹配的采集数据，请先保存新样本")
        result_path = samples.with_name(f"{samples.stem}_result.yaml")
        if name == "verify" and (not result_path.exists() or
                                  result_path.stat().st_mtime_ns < samples.stat().st_mtime_ns):
            raise ValueError("请先对当前采集数据重新求解，再进行验证")
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
        if not self._saved_samples_match_board(samples):
            raise ValueError("求解结果对应的棋盘采集数据不匹配，请重新采集并求解")
        if not result_path.exists():
            raise FileNotFoundError("尚无手眼求解结果")
        if result_path.stat().st_mtime_ns < samples.stat().st_mtime_ns:
            raise ValueError("结果已过期，请重新求解当前采集数据")
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

    def _cancel_servo_internal(self):
        self.servo_cancel.set()
        if self.servo_motion:
            self.servo_motion.cancel()

    @serialized
    def connect_servo_depth(self, params):
        if self.config.camera_source!='ros':
            raise ValueError('RGB-D 视觉伺服需要 ROS2 彩色图像话题，V4L2 模式不可用')
        topic=str(params.get('topic',self.config.aligned_depth_topic)).strip()
        if not topic.startswith('/'):
            raise ValueError('请选择对齐到彩色光学 Frame 的深度 Image 话题')
        if self.servo_thread and self.servo_thread.is_alive():
            raise ValueError('运动中不能切换深度流')
        if self.ros_depth.running:self.ros_depth.stop()
        if not self.mock:
            graph={x['topic']:x['types'] for x in discover_ros_topics()}
            if 'sensor_msgs/msg/Image' not in graph.get(topic,[]):
                raise ValueError('深度话题不存在或不是 sensor_msgs/msg/Image，请先搜索话题')
            self.ros_depth.start(topic)
        self.config.aligned_depth_topic=topic
        self.config.save(self.config_path)
        self.servo_target=None
        return {'topic':topic,'ready':self.ros_depth.running}

    def _servo_capture(self, after=0., tracking=False):
        if self.config.camera_source!='ros':
            raise ValueError('RGB-D 伺服只支持 ROS2 Image')
        frozen=load_frozen(self._validation_paths()[0])
        if not self.camera_open or not self.ros.running:
            raise ValueError('请先连接机械臂与 RGB 相机')
        with self.frame_lock:
            rgb=self.current_frame.copy() if self.current_frame is not None else None
            depth=self.depth_frame.copy() if self.depth_frame is not None else None
            rgb_time=self.frame_received_at;depth_time=self.depth_received_at
            rgb_stamp=self.frame_ros_stamp;depth_stamp=self.depth_stamp
            rgb_frame=self.frame_id;depth_frame=self.depth_frame_id
        now=time.monotonic()
        if rgb is None or depth is None or not rgb_time or not depth_time or now-rgb_time>.35 or now-depth_time>.35:
            raise ValueError('RGB 或对齐深度图已经过期')
        if after and (rgb_time<=after or depth_time<=after):
            raise ValueError('等待机械臂停稳后的新 RGB-D 数据')
        if rgb.shape[:2]!=depth.shape:
            raise ValueError('深度图与 RGB 分辨率不同，请由相机端发布彩色对齐深度')
        if rgb_frame!=depth_frame or rgb_frame!=frozen['camera_frame']:
            raise ValueError(f'深度、RGB 与冻结手眼矩阵的光学 Frame 不同: {depth_frame} / {rgb_frame} / {frozen["camera_frame"]}')
        if rgb_stamp is None or depth_stamp is None or abs(rgb_stamp-depth_stamp)>.05:
            raise ValueError('RGB 与 Depth 时间戳相差超过 50ms，请相机端完成同步')
        k,d,size=__import__('validation_engine')._intrinsics(frozen)
        if [rgb.shape[1],rgb.shape[0]]!=size:
            raise ValueError('实时 RGB 分辨率与求解时相机内参不一致')
        info=self.camera_info
        if info is None:
            raise ValueError('RGB-D 视觉伺服必须订阅 ROS2 CameraInfo，不能只凭历史内参文件推断当前光学模型')
        if info.get('frame_id')!=rgb_frame or [info.get('image_width'),info.get('image_height')]!=size:
            raise ValueError('CameraInfo 的光学 Frame 或图像尺寸与实时 RGB 不匹配')
        live_k=np.asarray(info['camera_matrix']['data'],dtype=float).reshape(3,3)
        if np.max(np.abs(live_k[:2,:2]-k[:2,:2]))>max(2.,float(np.max(np.abs(k[:2,:2])))*.02) or np.max(np.abs(live_k[:2,2]-k[:2,2]))>3.:
            raise ValueError('ROS2 CameraInfo 与手眼标定冻结内参差异过大，请确认当前相机模式与内参来源')
        if not self.robot_model:
            raise ValueError('请导入具有目标 Link 的 Description / URDF')
        entry,dt=self.pose_history.match(rgb_time,now)
        pose=self.latest_pose
        if pose is None or (pose.frame_id,pose.child_frame_id)!=(frozen['robot_base_frame'],frozen['robot_end_frame']):
            raise ValueError('机器人 Frame 与冻结手眼矩阵不一致')
        if entry['robot_timestamp'] and abs(float(entry['robot_timestamp'])-rgb_stamp)>.10:
            raise ValueError('机器人位姿与 RGB 图像 ROS 时间戳不匹配')
        base_end=self._spatial_base_tool(entry['pose'])
        x=np.asarray(frozen['handeye_transform'],dtype=float)
        return dict(rgb=rgb,depth=depth,k=k,d=d,rgb_time=rgb_time,stamp=rgb_stamp,
            base_end=base_end,x=x,frozen=frozen,dt_ms=dt)

    def _servo_tip_matrix(self,sample,link):
        end=sample['frozen']['robot_end_frame']
        offset=self.robot_model.transform(end,link,only_fixed=True)
        return sample['base_end']@offset

    @serialized
    def select_servo_target(self,params):
        if self.servo_thread and self.servo_thread.is_alive():
            raise ValueError('运动期间不能重新选择目标')
        snap=self._servo_capture()
        u=float(params.get('u',-1))*snap['rgb'].shape[1]
        v=float(params.get('v',-1))*snap['rgb'].shape[0]
        roi=params.get('roi') or {}
        if roi:
            rw=float(roi.get('width',0))*snap['rgb'].shape[1]
            rh=float(roi.get('height',0))*snap['rgb'].shape[0]
            if rw<8 or rh<8 or rw>180 or rh>180:
                raise ValueError('目标框的边长必须为 8～180 像素，请重新框选')
        else:
            rw=rh=0
        z=depth_at(snap['depth'],u,v)
        pt=pixel_to_point(u,v,z,snap['k'],snap['d'])
        base=camera_to_base(pt,snap['base_end'],snap['x'])
        tool=str(params.get('link',''))
        tip=self._servo_tip_matrix(snap,tool)
        template=make_template(snap['rgb'],u,v,radius=min(24,max(12,int(min(rw,rh)*.38))) if roi else 16)
        # Restrict ROI and approach to measured 3D target, not a stale pose
        self.servo_target=dict(u=round(u,2),v=round(v,2), depth_m=z,
            point_base_m=base.tolist(),link=tool,template=template,
            created_at=time.time(),stamp=snap['stamp'],frame=snap['frozen']['camera_frame'],
            roi_px=[round(rw),round(rh)] if roi else None,
            tip_m=tip[:3,3].tolist(),distance_m=float(np.linalg.norm(base-tip[:3,3])))
        self.servo_progress={'phase':'selected','step':0,'message':'目标已定位，请检查图像中的目标和目标 Link，再确认运动'}
        self.servo_history=[]
        self._emit_state()
        return {'target':{k:v for k,v in self.servo_target.items() if k!='template'}}

    @serialized
    def clear_servo_target(self, _params):
        if self.servo_thread and self.servo_thread.is_alive():
            raise ValueError('机械臂运动期间不允许修改目标，请先取消任务')
        self.servo_target=None
        self.servo_history=[]
        self.servo_progress={'phase':'idle','step':0,'message':'等待框选目标'}
        self._emit_state()
        return {'cleared':True}

    @serialized
    def set_servo_motion_config(self, params):
        if self.servo_thread and self.servo_thread.is_alive():
            raise ValueError('运动时不能修改 Action 配置')
        name=str(params.get('action','')).strip();group=str(params.get('group','')).strip()
        if not name.startswith('/') or not group or any(x.isspace() for x in group):
            raise ValueError('运动 Action 必须是绝对 ROS2 名称，规划组不能为空')
        self.config.motion_action=name;self.config.motion_group=group
        self.config.save(self.config_path)
        self.servo_target=None
        return {'action':name,'group':group}

    def _servo_observe(self, previous, after=0.):
        sample=self._servo_capture(after=after)
        target=self.servo_target
        pixel=project_base(previous,sample['base_end'],sample['x'],sample['k'],sample['d'])
        u,v,score=track_template(sample['rgb'],target['template'],*pixel)
        z=depth_at(sample['depth'],u,v)
        measured=camera_to_base(pixel_to_point(u,v,z,sample['k'],sample['d']),sample['base_end'],sample['x'])
        if np.linalg.norm(measured-previous)>.045:
            raise ValueError('目标重新识别的位置发生超过 45mm 跳变，停止运动')
        target['u']=round(float(u),2)
        target['v']=round(float(v),2)
        target['depth_m']=float(z)
        target['tracking_score']=float(score)
        return sample,measured,score

    def _servo_emit(self,phase,step,message):
        self.servo_progress=dict(phase=phase,step=step,message=message)
        self._emit('servo_progress',self._servo_state())

    def _servo_worker(self, params):
        motion=None
        try:
            link=self.servo_target['link']
            target=np.asarray(self.servo_target['point_base_m'],float)
            step=float(params['step_m']);clearance=float(params['clearance_m']);max_steps=int(params['max_steps'])
            motion=MoveGroupMotion(self.config.motion_action,self.config.motion_group,timeout=18.,velocity=.06)
            self.servo_motion=motion
            for index in range(max_steps):
                if self.servo_cancel.is_set():raise RuntimeError('伺服已取消')
                self._servo_emit('observing',index,'正在检查停稳位姿、同步深度和目标跟踪')
                if index==0:
                    if time.time()-self.servo_target['created_at']>15:
                        raise ValueError('目标选择已超过 15 秒，请重新框选')
                    sample,current_target,score=self._servo_observe(target)
                    target=current_target
                else:
                    deadline=time.monotonic()+3.
                    while True:
                        if self.servo_cancel.is_set():raise RuntimeError('伺服已取消')
                        try:
                            sample,current_target,score=self._servo_observe(target,after=post_motion)
                            break
                        except ValueError as exc:
                            if time.monotonic()>deadline:raise RuntimeError(f'运动后视觉确认失败: {exc}')
                            time.sleep(.12)
                    target=current_target
                tip=self._servo_tip_matrix(sample,link)
                next_xyz,distance,done=limited_step(tip[:3,3],target,step,clearance)
                record={'step':index+1,'distance_mm':round(distance*1000,2),'target_base_m':target.tolist(),
                        'tip_base_m':tip[:3,3].tolist(),'stamp':sample['stamp'],'depth_frame':self.depth_frame_id}
                self.servo_history.append(record)
                if done:
                    self._servo_emit('completed',index, f'已到达距离目标 {distance*1000:.1f} mm 的安全范围，未下发接触动作')
                    break
                self._servo_emit('moving',index+1,f'向机器人 {self.config.motion_action} 提交单步 {step*1000:.0f} mm 以内的规划运动')
                pose=pose_from_matrix(tip)
                motion.execute(sample['frozen']['robot_base_frame'],link,next_xyz,pose[3:],
                    feedback=lambda msg:self._emit('servo_feedback',{'text':msg,'step':index+1}))
                post_motion=time.monotonic()+.4
                self._servo_emit('settling',index+1,'运动已返回成功，等待新的停稳 RGB-D 观测')
                time.sleep(.4)
            else:
                self._servo_emit('incomplete',max_steps,'达到迭代次数限制，请检查剩余误差后重新选择目标')
            report=dict(kind='rgbd_discrete_visual_servo',result=self.servo_progress,
                action=self.config.motion_action,group=self.config.motion_group,link=link,
                clearance_mm=clearance*1000,history=self.servo_history,
                note='仅为运动学估计误差，不是独立接触或计量精度')
            path=self._paths()[0]/'rgbd_servo_report.yaml'
            path.write_text(yaml.safe_dump(report,sort_keys=False,allow_unicode=True),encoding='utf-8')
            self._emit('servo_finished',{'report_path':str(path),'status':self.servo_progress['phase']})
        except Exception as exc:
            self._servo_emit('cancelled' if self.servo_cancel.is_set() else 'failed',
                self.servo_progress.get('step',0),str(exc))
            try:
                report=dict(kind='rgbd_discrete_visual_servo',result=self.servo_progress,
                    action=self.config.motion_action,group=self.config.motion_group,
                    link=self.servo_target['link'] if self.servo_target else '',
                    history=self.servo_history,
                    note='仅为机器人运动学与 RGB-D 定位估计，不能作为实际接触精度')
                path=self._paths()[0]/'rgbd_servo_report.yaml'
                path.write_text(yaml.safe_dump(report,sort_keys=False,allow_unicode=True),encoding='utf-8')
                self._emit('servo_finished',{'report_path':str(path),'status':self.servo_progress['phase']})
            except Exception:
                pass
        finally:
            self.servo_motion=None
            self._emit_state()

    def check_servo_motion(self, _params):
        if self.mock:
            return {'available':False,'reason':'演示模式未连接真实 MoveGroup Action'}
        try:
            import rclpy
            from rclpy.action import ActionClient
            from moveit_msgs.action import MoveGroup
        except ImportError:
            return {'available':False,'reason':'缺少 ROS2 moveit_msgs/action/MoveGroup，请安装与 ROS2 发行版匹配的 MoveIt2'}
        if not rclpy.ok():rclpy.init(args=None)
        node=rclpy.create_node('handeye_servo_action_check')
        client=ActionClient(node,MoveGroup,self.config.motion_action)
        try:
            available=client.wait_for_server(timeout_sec=1.0)
            return {'available':bool(available),'action':self.config.motion_action,
                    'group':self.config.motion_group,
                    'reason':'Action 服务已发现，实际规划组与工具 Link 是否可用仍需由机器人执行时验证' if available else '未发现指定 MoveGroup Action，请检查机器人端 MoveIt2 与 Action 名称'}
        finally:
            client.destroy();node.destroy_node()

    @serialized
    def start_servo(self,params):
        if self.mock:
            raise ValueError('演示模式禁止下发机械臂运动')
        if self.servo_thread and self.servo_thread.is_alive():
            raise ValueError('已有伺服任务在运行')
        if not self.servo_target:
            raise ValueError('请先在实时 RGB 图像上选择三维目标点')
        if self.active_job:
            raise ValueError('当前正在进行标定计算，禁止同时执行伺服')
        step=float(params.get('step_m',.015))
        clearance=float(params.get('clearance_m',.035))
        count=int(params.get('max_steps',8))
        if not (.003<=step<=.03 and .025<=clearance<=.20 and 1<=count<=20):
            raise ValueError('单步距离 3~30mm，安全间距 25~200mm，迭代次数 1~20')
        if params.get('confirm')!='I_UNDERSTAND_ROBOT_MOTION':
            raise ValueError('必须确认运动可能带来碰撞风险，并且机器人端已启用限位、碰撞检测、急停和取消')
        self._servo_capture()
        self.servo_cancel.clear()
        self.servo_thread=threading.Thread(target=self._servo_worker,
            args=({'step_m':step,'clearance_m':clearance,'max_steps':count},),daemon=True,name='handeye-rgbd-servo')
        self.servo_thread.start()
        return {'started':True}

    def cancel_servo(self,_params):
        self._cancel_servo_internal()
        self.servo_progress=dict(phase='cancelling',step=self.servo_progress.get('step',0),
            message='已请求取消运动，请确认机器人实际停止')
        return {'requested':True}

    def dispatch(self, method: str, params: dict[str, Any]) -> Any:
        if method == "ping":
            return {"pong": True, "python": sys.version.split()[0], "mock": self.mock}
        if method == "get_state":
            return self._state()
        if method == "set_config":
            return self._apply_config(params)
        if method == "switch_project":
            return self.switch_project(params)
        if method == "check_spatial_camera":
            return self.check_spatial_camera(params)
        if method == "update_board":
            return self.update_board(params)
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
        if method == 'get_model_preview':
            return self.get_model_preview(params)
        if method == 'import_robot_model':
            return self.import_robot_model(params)
        if method == 'import_ros_model':
            return self.import_ros_model(params)
        if method == 'clear_robot_model':
            return self.clear_robot_model(params)
        if method == 'resolve_tool_link':
            return self.resolve_tool_link(params)
        if method == 'record_spatial_contact':
            return self.record_spatial_contact(params)
        if method == 'measure_spatial_target':
            return self.measure_spatial_target(params)
        if method == 'clear_spatial':
            return self.clear_spatial(params)
        if method == 'connect_servo_depth':
            return self.connect_servo_depth(params)
        if method == 'select_servo_target':
            return self.select_servo_target(params)
        if method == 'set_servo_motion_config':
            return self.set_servo_motion_config(params)
        if method == 'clear_servo_target':
            return self.clear_servo_target(params)
        if method == 'check_servo_motion':
            return self.check_servo_motion(params)
        if method == 'start_servo':
            return self.start_servo(params)
        if method == 'cancel_servo':
            return self.cancel_servo(params)
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
        if method == "import_samples":
            return self.import_samples(params)
        if method == "delete_samples":
            return self.delete_samples(params)
        if method == 'freeze_validation':
            return self.freeze_validation(params)
        if method == 'import_validation':
            return self.import_validation(params)
        if method == 'set_validation_overlay':
            return self.set_validation_overlay(params)
        if method == 'capture_validation':
            return self.capture_validation(params)
        if method == 'clear_validation':
            return self.clear_validation(params)
        if method == 'export_validation':
            return self.export_validation(params)
        if method == "start_tool":
            return self.start_tool(params)
        if method == "cancel_tool":
            return self.cancel_tool(params)
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
        self._cancel_servo_internal()
        if self.active_job:
            self.cancel_tool({"id": self.active_job["id"]})
        if self._camera_thread.is_alive() and self._camera_thread is not threading.current_thread():
            self._camera_thread.join(timeout=2.0)
        self._cancel_servo_internal()
        try:
            self.ros_depth.stop()
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
