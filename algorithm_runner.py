from __future__ import annotations

import contextlib
import importlib
import sys
import traceback
from pathlib import Path
from typing import Callable

import numpy as np


class _EventStream:
    def __init__(self, emit: Callable[[str], None]):
        self._emit = emit

    def write(self, text: str) -> int:
        if text:
            self._emit(text)
        return len(text)

    def flush(self) -> None:
        return None


def joints_to_pose(joints_rad) -> tuple[float, float, float, float, float, float, float]:
    """Convert configured robot joint angles (rad) to x y z qx qy qz qw."""
    algorithm_dir = Path(__file__).resolve().parent / "algorithms"
    algorithm_text = str(algorithm_dir)
    if algorithm_text not in sys.path:
        sys.path.insert(0, algorithm_text)
    fk_utils = importlib.import_module("fk_utils")
    transform = fk_utils.fk_gripper_in_base(joints_rad)
    quaternion = fk_utils.matrix_to_quaternion(np.asarray(transform)[:3, :3])
    translation = np.asarray(transform)[:3, 3]
    return tuple(float(v) for v in (*translation, *quaternion))


def run_algorithm(
    name: str,
    samples_path: Path,
    solve_mode: str,
    emit: Callable[[str], None],
) -> int:
    """Run the bundled algorithms in-process and stream text to the GUI."""
    algorithm_dir = Path(__file__).resolve().parent / "algorithms"
    if not (algorithm_dir / "solve.py").exists():
        emit(f"内置算法目录不存在：{algorithm_dir}\n")
        return 1
    algorithm_text = str(algorithm_dir)
    if algorithm_text not in sys.path:
        sys.path.insert(0, algorithm_text)
    importlib.invalidate_caches()
    stream = _EventStream(emit)
    try:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            if name == "diagnose":
                module = importlib.import_module("diagnose")
                module.diagnose(str(samples_path))
                return 0
            if name == "solve":
                module = importlib.import_module("solve")
                result = module.solve(
                    str(samples_path),
                    simple=solve_mode == "minimal",
                    use_ba=solve_mode == "ba",
                )
                return 0 if result is not None else 1
            raise ValueError(f"未知算法任务：{name}")
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    except Exception:
        emit(traceback.format_exc())
        return 1


if __name__ == "__main__":
    import argparse
    import json
    import pickle
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True, choices=("intrinsic", "diagnose", "solve"))
    parser.add_argument("--samples", default="")
    parser.add_argument("--mode", default="robust")
    parser.add_argument("--snapshot", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--quality", default="standard")
    parser.add_argument("--board", default="{}")
    args = parser.parse_args()
    if args.job == "intrinsic":
        try:
            with open(args.snapshot, "rb") as f:
                calibration = pickle.load(f)
            board = json.loads(args.board)
            result = calibration.solve(Path(args.output),
                                       int(board.get("cols", board.get("squares_x", 0))),
                                       int(board.get("rows", board.get("squares_y", 0))),
                                       float(board.get("square_size_mm", 0)),
                                       quality_mode=args.quality, board=board)
            print("HANDEYE_JOB_RESULT:" + json.dumps(result, ensure_ascii=False), flush=True)
            sys.exit(0)
        except Exception:
            traceback.print_exc()
            sys.exit(1)
    sys.exit(run_algorithm(args.job, Path(args.samples), args.mode, sys.stdout.write))
