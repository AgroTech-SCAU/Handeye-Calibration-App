from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
PORTABLE_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else APP_DIR
)


def find_default_calib_dir() -> Path:
    return (APP_DIR / "algorithms").resolve()


@dataclass
class AppConfig:
    calib_dir: str = str(find_default_calib_dir())
    output_dir: str = str((PORTABLE_DIR / "output").resolve())
    camera_source: str = "ros"
    image_topic: str = ""
    camera_info_topic: str = ""
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    chessboard_cols: int = 11
    chessboard_rows: int = 8
    square_size_mm: float = 15.0
    board_type: str = "chessboard"
    charuco_squares_x: int = 14
    charuco_squares_y: int = 9
    charuco_marker_size_mm: float = 15.0
    charuco_dictionary: str = "DICT_5X5_100"
    charuco_min_corners: int = 6
    charuco_legacy_pattern: bool = False
    ros_input_type: str = "pose"
    robot_base_frame: str = ""
    robot_end_frame: str = ""
    camera_frame: str = ""
    pose_topic: str = ""
    joint_dof: int = 5
    joint_names: str = ""
    capture_topic: str = "/handeye/capture"
    status_topic: str = "/handeye/status"

    def board_config(self):
        if self.board_type == "chessboard":
            return dict(type="chessboard", cols=self.chessboard_cols, rows=self.chessboard_rows, square_size_mm=self.square_size_mm)
        return dict(type=self.board_type, squares_x=self.charuco_squares_x, squares_y=self.charuco_squares_y,
            square_size_mm=self.square_size_mm, marker_size_mm=self.charuco_marker_size_mm,
            dictionary=self.charuco_dictionary, min_corners=self.charuco_min_corners, legacy_pattern=self.charuco_legacy_pattern)

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        known = cls.__dataclass_fields__
        return cls(**{key: value for key, value in data.items() if key in known})

    def save(self, path: Path) -> None:
        path.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
