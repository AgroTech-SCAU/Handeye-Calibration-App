from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GIT_BLOBS = {
    "algorithm_runner.py": "6e9bf7c458039bf16262671b8d6de4084550bf76",
    "calibration_engine.py": "cae69a161b626752d404cd79a8d65c98359bcb58",
    "config.py": "34f31d27651d3541c6634ba21a77af7eba17480b",
    "ros_interface.py": "28b5ef4e1628f883ec66f350dc34258dd9c9a58c",
    "algorithms/bundle_adjust.py": "20769f84af5dad4406f6b3dbdcc5175b14bee23c",
    "algorithms/calib_utils.py": "621f8c53c11d462977f52fdb6d659285d6a760f5",
    "algorithms/diagnose.py": "fbcc17c122c2d960a4b50a2f9c8a9df377e861b3",
    "algorithms/fk_utils.py": "d921fa02c521905b5651d7d5811317ae56d4d568",
    "algorithms/robot_params.yaml": "145750751916a4668bdae958bf3f5191e03129d9",
    "algorithms/solve.py": "491b08e933eaa87f92d51469dbc485f59fcb5d53",
    "algorithms/verify.py": "dfe2fd63afa2aa94009072989c5fe4e1a764c821",
}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    payload = f"blob {len(data)}\0".encode() + data
    return hashlib.sha1(payload).hexdigest()


class UpstreamCoreIntegrityTests(unittest.TestCase):
    def test_frozen_core_is_byte_exact_github_main(self) -> None:
        mismatches = {
            rel: (git_blob_sha(ROOT / rel), expected)
            for rel, expected in EXPECTED_GIT_BLOBS.items()
            if git_blob_sha(ROOT / rel) != expected
        }
        self.assertEqual(mismatches, {})


if __name__ == "__main__":
    unittest.main()
