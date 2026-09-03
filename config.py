from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
CONFIG_DIR = Path.home() / ".config" / "handeye-calibration"
CONFIG_PATH = CONFIG_DIR / "config.json"


def default_output_dir() -> Path:
    return (Path.home() / "HandEyeCalibration" / "output").resolve()


@dataclass
class AppConfig:
    output_dir: str = str(default_output_dir())
    chessboard_cols: int = 11
    chessboard_rows: int = 8
    square_size_mm: float = 15.0
    pose_topic: str = ""
    image_topic: str = ""
    camera_info_topic: str = ""
    appearance_mode: str = "System"

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "AppConfig":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        known = cls.__dataclass_fields__
        return cls(**{key: value for key, value in data.items() if key in known})

    def save(self, path: Path = CONFIG_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
