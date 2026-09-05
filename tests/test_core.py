import tempfile
import unittest
from pathlib import Path

import numpy as np

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorithm_runner import joints_to_pose
from calibration_engine import (
    make_transform,
    object_points,
    quaternion_to_matrix,
    rpy_to_quaternion,
)
from config import AppConfig


class CoreTests(unittest.TestCase):
    def test_object_points_are_meters(self):
        points = object_points(3, 2, 20)
        self.assertEqual(points.shape, (6, 3))
        self.assertAlmostEqual(float(points[-1, 0]), 0.04)
        self.assertAlmostEqual(float(points[-1, 1]), 0.02)

    def test_identity_quaternion(self):
        rotation = quaternion_to_matrix(0, 0, 0, 1)
        np.testing.assert_allclose(rotation, np.eye(3), atol=1e-12)
        transform = make_transform(rotation, (1, 2, 3))
        np.testing.assert_allclose(transform[:3, 3], (1, 2, 3))

    def test_zero_rpy_is_identity_quaternion(self):
        self.assertEqual(rpy_to_quaternion(0, 0, 0), (0.0, 0.0, 0.0, 1.0))

    def test_five_joint_fk_returns_pose(self):
        pose = joints_to_pose([0, 0, 0, 0, 0])
        self.assertEqual(len(pose), 7)
        self.assertTrue(np.all(np.isfinite(pose)))

    def test_wrong_joint_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "5 自由度"):
            joints_to_pose([0, 0, 0, 0, 0, 0])

    def test_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            expected = AppConfig(camera_index=2, pose_topic="/robot/pose")
            expected.save(path)
            actual = AppConfig.load(path)
            self.assertEqual(actual.camera_index, 2)
            self.assertEqual(actual.pose_topic, "/robot/pose")


if __name__ == "__main__":
    unittest.main()
