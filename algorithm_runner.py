from __future__ import annotations

import contextlib
import importlib
import sys
import traceback
from pathlib import Path
from typing import Callable


class _EventStream:
    def __init__(self, emit: Callable[[str], None]):
        self._emit = emit

    def write(self, text: str) -> int:
        if text:
            self._emit(text)
        return len(text)

    def flush(self) -> None:
        return None


def run_algorithm(
    name: str,
    samples_path: Path,
    solve_mode: str,
    emit: Callable[[str], None],
) -> int:
    """Run the bundled, already-validated calibration algorithms in-process."""
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
            if name == "verify":
                module = importlib.import_module("verify")
                result_path = samples_path.with_name(f"{samples_path.stem}_result.yaml")
                old_argv = sys.argv
                try:
                    sys.argv = ["verify.py", str(samples_path), "--result", str(result_path)]
                    module.main()
                finally:
                    sys.argv = old_argv
                return 0
            raise ValueError(f"未知算法任务：{name}")
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    except Exception:
        emit(traceback.format_exc())
        return 1
