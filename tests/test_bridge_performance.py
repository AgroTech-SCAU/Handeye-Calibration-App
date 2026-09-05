from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BridgePerformanceContractTests(unittest.TestCase):
    def test_preview_target_is_ten_fps(self) -> None:
        text = (ROOT / "backend" / "bridge.py").read_text(encoding="utf-8")
        self.assertIn("PREVIEW_INTERVAL_SEC = 0.10", text)
        self.assertIn("time.sleep(PREVIEW_INTERVAL_SEC)", text)


if __name__ == "__main__":
    unittest.main()
