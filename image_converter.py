from __future__ import annotations

import cv2
import numpy as np


_ENCODING_CHANNELS = {
    "mono8": 1,
    "bgr8": 3,
    "rgb8": 3,
    "bgra8": 4,
    "rgba8": 4,
}


def image_message_to_bgr(message) -> np.ndarray:
    """Convert a sensor_msgs/Image-like object to a contiguous BGR uint8 frame.

    The function intentionally does not depend on cv_bridge so the application can
    use the ROS installation's Python ABI without an extra binary dependency.
    """
    encoding = str(message.encoding).lower()
    channels = _ENCODING_CHANNELS.get(encoding)
    if channels is None:
        raise ValueError(
            f"不支持的 ROS Image encoding: {message.encoding}；"
            "v1 支持 mono8 / bgr8 / rgb8 / bgra8 / rgba8"
        )

    width = int(message.width)
    height = int(message.height)
    step = int(message.step)
    if width <= 0 or height <= 0:
        raise ValueError("ROS Image 的 width/height 必须大于 0")

    row_bytes = width * channels
    if step < row_bytes:
        raise ValueError(f"ROS Image step={step} 小于每行有效字节数 {row_bytes}")

    raw = np.frombuffer(message.data, dtype=np.uint8)
    required = height * step
    if raw.size < required:
        raise ValueError(f"ROS Image data 长度不足：需要 {required} 字节，实际 {raw.size} 字节")

    rows = raw[:required].reshape(height, step)
    pixels = rows[:, :row_bytes]
    if channels == 1:
        mono = pixels.reshape(height, width)
        return cv2.cvtColor(mono, cv2.COLOR_GRAY2BGR)

    frame = pixels.reshape(height, width, channels)
    if encoding == "bgr8":
        return np.ascontiguousarray(frame)
    if encoding == "rgb8":
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    if encoding == "bgra8":
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    return cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
