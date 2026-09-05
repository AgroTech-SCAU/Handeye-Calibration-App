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
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    chessboard_cols: int = 11
    chessboard_rows: int = 8
    square_size_mm: float = 15.0
    ros_input_type: str = "pose"
    pose_topic: str = "/arm/pose"
    joint_dof: int = 5
    joint_names: str = ""
    capture_topic: str = "/handeye/capture"
    status_topic: str = "/handeye/status"

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
