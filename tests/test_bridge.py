from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]


class BridgeProcess:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        env = os.environ.copy()
        env["HANDEYE_MOCK"] = "1"
        env["HANDEYE_DATA_DIR"] = self.temp.name
        self.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "backend" / "bridge.py")],
            cwd=ROOT,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        assert self.proc.stdin and self.proc.stdout
        self.seq = 0
        ready = self.read_until(lambda msg: msg.get("kind") == "event" and msg.get("event") == "ready")
        assert ready["data"]["mock"] is True

    def read_until(self, predicate, timeout: float = 8.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                if self.proc.poll() is not None:
                    stderr = self.proc.stderr.read() if self.proc.stderr else ""
                    raise AssertionError(f"bridge exited early: {self.proc.returncode}\n{stderr}")
                continue
            msg = json.loads(line)
            if predicate(msg):
                return msg
        raise TimeoutError("bridge response timeout")

    def request(self, method: str, params=None, timeout: float = 8.0):
        self.seq += 1
        req_id = self.seq
        self.proc.stdin.write(json.dumps({"id": req_id, "method": method, "params": params or {}}) + "\n")
        self.proc.stdin.flush()
        msg = self.read_until(lambda item: item.get("kind") == "response" and item.get("id") == req_id, timeout)
        return msg

    def close(self) -> None:
        if self.proc.poll() is None:
            try:
                self.request("shutdown")
            except Exception:
                pass
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                self.proc.kill()
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass
        self.temp.cleanup()


class BridgeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = BridgeProcess()

    def tearDown(self) -> None:
        self.bridge.close()

    def test_first_run_keeps_ros_capture_trigger_disabled(self) -> None:
        state = self.bridge.request("get_state")["result"]
        self.assertEqual(state["config"]["capture_topic"], "")

    def test_ping_and_state(self) -> None:
        ping = self.bridge.request("ping")
        self.assertTrue(ping["ok"])
        self.assertTrue(ping["result"]["pong"])
        self.assertTrue(ping["result"]["mock"])

        state = self.bridge.request("get_state")["result"]
        self.assertIn("config", state)
        self.assertIn("camera", state)
        self.assertIn("ros", state)
        self.assertEqual(state["intrinsics"]["count"], 0)
        self.assertEqual(state["handeye"]["count"], 0)

    def test_mock_camera_produces_preview_and_intrinsic_capture(self) -> None:
        opened = self.bridge.request("open_camera")
        self.assertTrue(opened["ok"])
        preview = self.bridge.read_until(lambda msg: msg.get("kind") == "event" and msg.get("event") == "preview", timeout=10)
        self.assertTrue(preview["data"]["jpeg"])
        self.assertGreater(preview["data"]["width"], 0)
        self.assertGreater(preview["data"]["height"], 0)

        captured = self.bridge.request("capture_intrinsic", {"quality_mode": "minimal"}, timeout=10)
        self.assertTrue(captured["ok"], captured)
        self.assertEqual(captured["result"]["count"], 1)

    def test_mock_intrinsics_and_handeye_sample_roundtrip(self) -> None:
        self.bridge.request("open_camera")
        self.bridge.read_until(
            lambda msg: msg.get("kind") == "event" and msg.get("event") == "preview",
            timeout=10,
        )
        for _ in range(3):
            captured = self.bridge.request("capture_intrinsic", {"quality_mode": "minimal"}, timeout=10)
            self.assertTrue(captured["ok"], captured)
        solved = self.bridge.request("solve_intrinsic", {"quality_mode": "minimal"}, timeout=20)
        self.assertTrue(solved["ok"], solved)
        self.assertEqual(solved["result"]["captured_images"], 3)

        sample = self.bridge.request(
            "capture_handeye",
            {
                "mode": "manual",
                "manual_type": "quaternion",
                "values": [0.30, 0.00, 0.42, 0.0, 0.0, 0.0, 1.0],
                "quality_mode": "minimal",
            },
            timeout=10,
        )
        self.assertTrue(sample["ok"], sample)
        self.assertEqual(sample["result"]["count"], 1)
        saved = self.bridge.request("save_samples", timeout=10)
        self.assertTrue(saved["ok"], saved)
        self.assertTrue(Path(saved["result"]["path"]).exists())

    def test_diagnose_streams_algorithm_log_without_breaking_protocol(self) -> None:
        self.bridge.request("open_camera")
        self.bridge.read_until(
            lambda msg: msg.get("kind") == "event" and msg.get("event") == "preview",
            timeout=10,
        )
        for _ in range(3):
            self.assertTrue(self.bridge.request(
                "capture_intrinsic", {"quality_mode": "minimal"}, timeout=10
            )["ok"])
        self.assertTrue(self.bridge.request(
            "solve_intrinsic", {"quality_mode": "minimal"}, timeout=20
        )["ok"])
        self.assertTrue(self.bridge.request(
            "capture_handeye",
            {
                "mode": "manual",
                "manual_type": "quaternion",
                "values": [0.30, 0.00, 0.42, 0.0, 0.0, 0.0, 1.0],
                "quality_mode": "minimal",
            },
            timeout=10,
        )["ok"])
        self.assertTrue(self.bridge.request("save_samples", timeout=10)["ok"])
        result = self.bridge.request(
            "run_tool", {"name": "diagnose", "solve_mode": "robust"}, timeout=30
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["result"]["exit_code"], 0)
        self.assertIn("标定数据诊断", result["result"]["log"])

    def test_solve_tool_returns_result_over_json_protocol(self) -> None:
        state = self.bridge.request("get_state")["result"]
        samples_path = Path(state["handeye"]["samples_path"])
        samples_path.parent.mkdir(parents=True, exist_ok=True)

        def transform(rvec, t):
            matrix = np.eye(4, dtype=float)
            matrix[:3, :3] = cv2.Rodrigues(np.asarray(rvec, dtype=float))[0]
            matrix[:3, 3] = np.asarray(t, dtype=float)
            return matrix

        x = transform([0.08, -0.04, 0.03], [0.045, -0.018, 0.082])
        y = transform([0.02, 0.03, -0.02], [0.56, 0.02, 0.31])
        motions = [
            ([0.00, 0.00, 0.00], [0.30, -0.08, 0.42]),
            ([0.16, 0.02, 0.03], [0.34, -0.02, 0.45]),
            ([-0.10, 0.14, 0.01], [0.28, 0.04, 0.40]),
            ([0.04, -0.12, 0.15], [0.36, 0.01, 0.38]),
            ([0.18, 0.10, -0.08], [0.31, 0.08, 0.46]),
            ([-0.14, -0.06, 0.12], [0.25, -0.01, 0.44]),
            ([0.08, 0.17, 0.11], [0.33, 0.05, 0.35]),
            ([-0.07, 0.09, -0.16], [0.27, -0.06, 0.37]),
        ]
        samples = []
        for index, (rv, tv) in enumerate(motions, 1):
            a = transform(rv, tv)
            b = np.linalg.inv(x) @ np.linalg.inv(a) @ y
            samples.append({
                "id": index,
                "gripper_in_base": a.tolist(),
                "target_to_camera": b.tolist(),
                "reprojection_error_px": 0.10,
                "laplacian_variance": 180.0,
                "corner_rms_px": 0.05,
            })
        samples_path.write_text(yaml.safe_dump({
            "handeye_mode": "eye_in_hand",
            "sample_count": len(samples),
            "samples": samples,
        }, sort_keys=False), encoding="utf-8")

        result = self.bridge.request(
            "run_tool", {"name": "solve", "solve_mode": "minimal"}, timeout=30
        )
        self.assertTrue(result["ok"], result)
        payload = result["result"].get("result")
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["handeye_mode"], "eye_in_hand")
        self.assertEqual(payload["total_samples"], len(samples))
        self.assertLess(payload["translation_rms_mm"], 1e-3)
        self.assertLess(payload["rotation_rms_deg"], 1e-3)

    def test_manual_pose_validation_is_reported_as_protocol_error(self) -> None:
        self.bridge.request("open_camera")
        self.bridge.read_until(lambda msg: msg.get("kind") == "event" and msg.get("event") == "preview", timeout=10)
        bad = self.bridge.request(
            "capture_handeye",
            {"mode": "manual", "manual_type": "quaternion", "values": [0, 0, 0]},
        )
        self.assertFalse(bad["ok"])
        self.assertIn("7 个值", bad["error"])


if __name__ == "__main__":
    unittest.main()
