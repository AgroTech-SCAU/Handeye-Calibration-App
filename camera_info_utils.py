from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml


def camera_info_payload(message) -> dict:
    matrix = [float(value) for value in message.k]
    distortion = [float(value) for value in message.d]
    if len(matrix) != 9:
        raise ValueError(f"CameraInfo.k 应包含 9 个值，实际为 {len(matrix)}")
    if matrix[0] <= 0.0 or matrix[4] <= 0.0:
        raise ValueError("CameraInfo 表示相机尚未标定（fx/fy <= 0）")
    if int(message.width) <= 0 or int(message.height) <= 0:
        raise ValueError("CameraInfo width/height 必须大于 0")

    return {
        "camera_matrix": {"rows": 3, "cols": 3, "data": matrix},
        "distortion_coefficients": {
            "rows": 1,
            "cols": len(distortion),
            "data": distortion,
        },
        "distortion_model": str(getattr(message, "distortion_model", "")),
        "image_width": int(message.width),
        "image_height": int(message.height),
        "calibration_mode": "ros_camera_info",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def save_camera_info_intrinsics(output: Path, message) -> dict:
    payload = camera_info_payload(message)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return payload
