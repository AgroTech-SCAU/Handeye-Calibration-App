from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
import yaml

from calibration_board import CalibrationBoard, reprojection_rms, solve_board_pose


def object_points(cols: int, rows: int, square_size_mm: float) -> np.ndarray:
    points = np.zeros((cols * rows, 3), np.float32)
    points[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)
    points *= square_size_mm / 1000.0
    return points


def detect_chessboard(gray: np.ndarray, pattern: tuple[int, int]):
    corners = None
    if hasattr(cv2, "findChessboardCornersSB"):
        found, corners = cv2.findChessboardCornersSB(
            gray, pattern, flags=cv2.CALIB_CB_NORMALIZE_IMAGE,
        )
    else:
        found = False
    if not found:
        found, corners = cv2.findChessboardCorners(
            gray,
            pattern,
            flags=cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE,
        )
    if not found or corners is None:
        return False, None
    corners = np.asarray(corners, dtype=np.float32).reshape(-1, 1, 2)
    refined = cv2.cornerSubPix(
        gray,
        corners,
        (5, 5),
        (-1, -1),
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001),
    )
    return True, refined


def quaternion_to_matrix(qx: float, qy: float, qz: float, qw: float) -> np.ndarray:
    norm = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    if norm < 1e-12:
        raise ValueError("四元数长度不能为 0")
    x, y, z, w = qx / norm, qy / norm, qz / norm, qw / norm
    return np.array([
        [1 - 2 * (y*y + z*z), 2 * (x*y - z*w), 2 * (x*z + y*w)],
        [2 * (x*y + z*w), 1 - 2 * (x*x + z*z), 2 * (y*z - x*w)],
        [2 * (x*z - y*w), 2 * (y*z + x*w), 1 - 2 * (x*x + y*y)],
    ], dtype=np.float64)


def rpy_to_quaternion(
    roll: float, pitch: float, yaw: float,
) -> tuple[float, float, float, float]:
    """Fixed-axis roll/pitch/yaw (rad), Rz(yaw) Ry(pitch) Rx(roll), to xyzw."""
    cr, sr = math.cos(roll * 0.5), math.sin(roll * 0.5)
    cp, sp = math.cos(pitch * 0.5), math.sin(pitch * 0.5)
    cy, sy = math.cos(yaw * 0.5), math.sin(yaw * 0.5)
    return (
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy,
        cr * cp * cy + sr * sp * sy,
    )


def make_transform(rotation: np.ndarray, translation: Sequence[float]) -> np.ndarray:
    matrix = np.eye(4, dtype=np.float64)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = translation
    return matrix


def load_intrinsics(path: Path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    camera_matrix = np.asarray(data["camera_matrix"]["data"], dtype=np.float64).reshape(3, 3)
    distortion = np.asarray(
        data["distortion_coefficients"]["data"], dtype=np.float64,
    ).reshape(-1, 1)
    return camera_matrix, distortion, data


def board_config(cols, rows, square_mm, config=None):
    return CalibrationBoard(config or dict(type="chessboard", cols=cols, rows=rows, square_size_mm=square_mm))


def intrinsic_binding(data):
    matrix = np.asarray(data["camera_matrix"]["data"], np.float64).reshape(3, 3)
    distortion = np.asarray(data["distortion_coefficients"]["data"], np.float64).reshape(-1)
    width, height = data.get("image_width"), data.get("image_height")
    if not np.isfinite(matrix).all() or not np.isfinite(distortion).all() or matrix[0,0] <= 0 or matrix[1,1] <= 0 or not np.allclose(matrix[2], [0,0,1]):
        raise ValueError("无效相机内参")
    if distortion.size not in (4,5,8,12,14) or not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        raise ValueError("内参必须包含有效畸变系数及图像分辨率")
    return dict(camera_matrix=matrix.ravel().tolist(), distortion=distortion.tolist(), image_size=[width,height], created_at=data.get("created_at"))


class CameraSession:
    def __init__(self):
        self.capture: cv2.VideoCapture | None = None

    def open(self, index: int, width: int, height: int) -> None:
        self.close()
        backend = cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else cv2.CAP_ANY
        capture = cv2.VideoCapture(index, backend)
        if not capture.isOpened() and backend != cv2.CAP_ANY:
            capture.release()
            capture = cv2.VideoCapture(index)
        if not capture.isOpened():
            raise RuntimeError(f"无法打开相机 {index}")
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.capture = capture

    def read(self) -> np.ndarray | None:
        if self.capture is None:
            return None
        ok, frame = self.capture.read()
        return frame if ok else None

    def close(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None


@dataclass
class IntrinsicCaptureResult:
    sharpness: float
    board_coverage_percent: float


class IntrinsicCalibration:
    def __init__(self):
        self.object_sets: list[np.ndarray] = []
        self.image_sets: list[np.ndarray] = []
        self.image_size: tuple[int, int] | None = None
        self.quality_mode: str | None = None
        self.board_spec = None
        self.binding = None

    def add(
        self, frame: np.ndarray, cols: int, rows: int, square_mm: float,
        quality_mode: str = "standard",
        board: dict | None = None,
    ) -> IntrinsicCaptureResult:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.quality_mode is not None and quality_mode != self.quality_mode:
            raise ValueError("采集中不能切换质量模式；请先清空内参图片")
        detector = board_config(cols, rows, square_mm, board)
        size = (gray.shape[1], gray.shape[0])
        if self.board_spec is not None and (detector.config != self.board_spec or size != self.image_size):
            raise ValueError("采集中不能切换标定板或图像分辨率，请先清空图片")
        detection = detector.detect(gray)
        corners = detection.image_points
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        _, _, board_width, board_height = cv2.boundingRect(corners)
        coverage = float(
            board_width * board_height / (gray.shape[1] * gray.shape[0]) * 100.0
        )
        thresholds = {
            "standard": (80.0, 3.0, "标准质量模式"),
            "strict": (120.0, 6.0, "严格质量模式"),
        }
        if quality_mode in thresholds:
            min_sharpness, min_coverage, label = thresholds[quality_mode]
            problems = []
            if sharpness < min_sharpness:
                problems.append(f"清晰度 {sharpness:.0f} < {min_sharpness:.0f}")
            if coverage < min_coverage:
                problems.append(f"棋盘覆盖 {coverage:.1f}% < {min_coverage:.0f}%")
            if problems:
                raise ValueError(f"{label}拒绝本次图片：" + "；".join(problems))
        elif quality_mode != "minimal":
            raise ValueError(f"未知内参采样质量模式：{quality_mode}")
        self.object_sets.append(detection.object_points.copy())
        self.board_spec = dict(detector.config)
        self.image_sets.append(corners)
        self.image_size = (gray.shape[1], gray.shape[0])
        self.quality_mode = quality_mode
        return IntrinsicCaptureResult(sharpness, coverage)

    def solve(
        self, output: Path, cols: int, rows: int, square_mm: float,
        quality_mode: str = "standard",
        board: dict | None = None,
    ) -> dict:
        if self.board_spec is not None and board_config(cols, rows, square_mm, board).config != self.board_spec:
            raise ValueError("求解配置与采集标定板不一致")
        minimums = {"minimal": 3, "standard": 10, "strict": 15}
        if quality_mode not in minimums:
            raise ValueError(f"未知内参求解模式：{quality_mode}")
        if self.quality_mode is not None and quality_mode != self.quality_mode:
            raise ValueError("求解模式与已采集图片模式不一致；请切回原模式")
        minimum = minimums[quality_mode]
        if len(self.image_sets) < minimum:
            raise ValueError(
                f"当前模式至少采集 {minimum} 张内参图片，已有 {len(self.image_sets)} 张"
            )
        assert self.image_size is not None
        rms, matrix, distortion, rvecs, tvecs = cv2.calibrateCamera(
            self.object_sets,
            self.image_sets,
            self.image_size,
            None,
            None,
            flags=0 if quality_mode == "minimal" else cv2.CALIB_FIX_K3,
        )
        per_image = []
        for obj, img, rvec, tvec in zip(
            self.object_sets, self.image_sets, rvecs, tvecs,
        ):
            projected, _ = cv2.projectPoints(obj, rvec, tvec, matrix, distortion)
            per_image.append(reprojection_rms(img, projected))
        payload = {
            "camera_matrix": {"rows": 3, "cols": 3, "data": matrix.reshape(-1).tolist()},
            "distortion_coefficients": {
                "rows": 1,
                "cols": int(distortion.size),
                "data": distortion.reshape(-1).tolist(),
            },
            "image_width": self.image_size[0],
            "image_height": self.image_size[1],
            **CalibrationBoard(self.board_spec).metadata(),
            "reprojection_error_definition": "point_rms_2d",
            "reprojection_error_px": float(rms),
            "reprojection_error_median_px": float(np.median(per_image)),
            "reprojection_error_max_px": float(max(per_image)),
            "reprojection_per_image_px": per_image,
            "captured_images": len(self.image_sets),
            "calibration_mode": f"gui_{quality_mode}",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8",
        )
        return payload


@dataclass
class SampleResult:
    reprojection_error_px: float
    distance_mm: float
    sharpness: float
    pixels_per_square: float


class HandEyeCollection:
    def __init__(self):
        self.samples: list[dict] = []
        self.quality_mode: str | None = None
        self.board_spec = None
        self.binding = None

    def add(
        self,
        frame: np.ndarray,
        pose: Sequence[float],
        intrinsics_path: Path,
        cols: int,
        rows: int,
        square_mm: float,
        input_mode: str,
        pose_timestamp: float | None = None,
        robot_pose_input: Sequence[float] | None = None,
        quality_mode: str = "standard",
        board: dict | None = None,
    ) -> SampleResult:
        if len(pose) != 7:
            raise ValueError("位姿必须是 x y z qx qy qz qw")
        if self.quality_mode is not None and quality_mode != self.quality_mode:
            raise ValueError("采集中不能切换质量模式；请先清空外参样本")
        matrix, distortion, intrinsics = load_intrinsics(intrinsics_path)
        binding = intrinsic_binding(intrinsics)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detector = board_config(cols, rows, square_mm, board)
        if [gray.shape[1], gray.shape[0]] != binding["image_size"]:
            raise ValueError("采集图像分辨率与相机内参不一致")
        if self.board_spec is not None and (self.board_spec != detector.config or self.binding != binding):
            raise ValueError("采集中不能更换标定板或内参，请先清空样本")
        if not np.isfinite(np.asarray(pose, np.float64)).all():
            raise ValueError("机器人位姿包含非有限数值")
        detection = detector.detect(gray, matrix, distortion)
        corners, obj = detection.image_points, detection.object_points
        target_to_camera, error = solve_board_pose(obj, corners, matrix, distortion)
        tvec = target_to_camera[:3,3].reshape(3,1)
        x, y, z, qx, qy, qz, qw = (float(value) for value in pose)
        gripper_in_base = make_transform(quaternion_to_matrix(qx, qy, qz, qw), (x, y, z))
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        distance_mm = float(tvec[2, 0] * 1000.0)
        pixels_per_square = (
            float(matrix[0, 0] * detector.config["square_size_mm"] / distance_mm)
            if distance_mm > 0 else 0.0
        )
        thresholds = {
            "standard": (0.40, 80.0, 20.0, "标准质量模式"),
            "strict": (0.25, 120.0, 25.0, "严格质量模式"),
        }
        if quality_mode in thresholds:
            max_error, min_sharpness, min_pixels, label = thresholds[quality_mode]
            problems = []
            if error > max_error:
                problems.append(f"重投影 {error:.3f}px > {max_error:.2f}px")
            if sharpness < min_sharpness:
                problems.append(f"清晰度 {sharpness:.0f} < {min_sharpness:.0f}")
            if pixels_per_square < min_pixels:
                problems.append(f"方格 {pixels_per_square:.1f}px < {min_pixels:.0f}px")
            if problems:
                raise ValueError(f"{label}拒绝本次样本：" + "；".join(problems))
        elif quality_mode != "minimal":
            raise ValueError(f"未知外参采样质量模式：{quality_mode}")
        sample = {
            "id": len(self.samples) + 1,
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "gripper_in_base": gripper_in_base.tolist(),
            "target_to_camera": target_to_camera.tolist(),
            "robot_pose_input": [
                float(value) for value in
                (robot_pose_input if robot_pose_input is not None else pose)
            ],
            "input_mode": input_mode,
            "quality_mode": quality_mode,
            "reprojection_error_px": error,
            "laplacian_variance": sharpness,
            "corner_rms_px": None,
            "corners_px": corners.reshape(-1).tolist(),
        }
        if pose_timestamp is not None:
            sample["pose_timestamp"] = float(pose_timestamp)
        if detection.ids is not None:
            sample["charuco_ids"] = detection.ids.tolist()
        self.board_spec = dict(detector.config)
        self.binding = binding
        self.intrinsics_snapshot = intrinsics
        self.samples.append(sample)
        self.quality_mode = quality_mode
        return SampleResult(error, distance_mm, sharpness, pixels_per_square)

    def save(
        self,
        output: Path,
        intrinsics_path: Path,
        cols: int,
        rows: int,
        square_mm: float,
        board: dict | None = None,
    ) -> None:
        if not self.samples:
            raise ValueError("还没有外参样本")
        _, _, current = load_intrinsics(intrinsics_path)
        if intrinsic_binding(current) != self.binding or board_config(cols, rows, square_mm, board).config != self.board_spec:
            raise ValueError("保存配置与采集条件不一致，请恢复采集内参和标定板")
        intrinsics = self.intrinsics_snapshot
        payload = {
            "schema_version": 2,
            "reprojection_error_definition": "point_rms_2d",
            "handeye_mode": "eye_in_hand",
            "sample_count": len(self.samples),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            **CalibrationBoard(self.board_spec).metadata(),
            "collection_quality_mode": self.quality_mode,
            "intrinsics_file": intrinsics_path.name,
            "intrinsics_created_at": intrinsics.get("created_at"),
            "camera_matrix_at_collection": intrinsics.get("camera_matrix"),
            "distortion_at_collection": intrinsics.get("distortion_coefficients"),
            "image_size_at_collection": [
                intrinsics.get("image_width"), intrinsics.get("image_height"),
            ],
            "samples": self.samples,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8",
        )
