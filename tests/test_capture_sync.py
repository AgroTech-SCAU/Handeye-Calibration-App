import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

class SyncTests(unittest.TestCase):
    def setUp(self):
        from capture_sync import PoseHistory
        self.history=PoseHistory()
        self.pose=(0.,0.,0.,0.,0.,0.,1.)
    def fill(self,moving=False):
        for i in range(7):
            pose=((i*.01 if moving else 0.),0.,0.,0.,0.,0.,1.)
            self.history.add(pose,10.+i*.06,robot_timestamp=100+i*.06)
    def test_nearest_pose_and_robot_timestamp_are_retained(self):
        self.fill();entry,dt=self.history.match(10.35,10.37)
        self.assertEqual(entry['robot_timestamp'],100.36)
        self.assertLess(dt,20)
    def test_stale_pose_rejected(self):
        self.fill()
        with self.assertRaises(ValueError):self.history.match(11.,11.)
    def test_moving_robot_rejected(self):
        self.fill(True)
        with self.assertRaises(ValueError):self.history.match(10.35,10.37)
    def test_stale_frame_rejected(self):
        self.fill()
        with self.assertRaises(ValueError):self.history.match(10.35,11.)
    def test_insufficient_stability_history_rejected(self):
        self.history.add(self.pose,10.35,robot_timestamp=100.)
        with self.assertRaises(ValueError):self.history.match(10.35,10.36)

    def test_high_rate_stationary_stream_keeps_time_window(self):
        for i in range(1000):self.history.add(self.pose,10+i*.001,robot_timestamp=100+i*.001)
        entry,dt=self.history.match(10.995,11.)
        self.assertLess(dt,10)
