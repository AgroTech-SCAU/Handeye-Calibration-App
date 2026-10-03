"""Receipt-time pairing for stopped-robot ROS capture, not exposure synchronization"""
from collections import deque
import threading
import numpy as np


class PoseHistory:
    def __init__(self):
        self.entries = deque(maxlen=300)
        self.lock = threading.Lock()

    def add(self, pose, received_at, robot_timestamp=None, robot_input=None, input_mode='ros_pose'):
        values = np.asarray(pose, dtype=np.float64)
        if values.shape != (7,) or not np.isfinite(values).all() or np.linalg.norm(values[3:]) < 1e-12:
            raise ValueError('机器人位姿无效')
        entry = dict(pose=tuple(values), received_at=received_at, robot_timestamp=robot_timestamp,
            robot_input=robot_input, input_mode=input_mode)
        if not np.isfinite(received_at):
            raise ValueError('无效接收时间')
        entry['bucket'] = int(received_at*200)
        with self.lock:
            if self.entries and self.entries[-1]['bucket'] == entry['bucket']:
                self.entries[-1] = entry
            else:
                self.entries.append(entry)
            while self.entries and received_at-self.entries[0]['received_at'] > .7:
                self.entries.popleft()

    def clear(self):
        with self.lock:
            self.entries.clear()

    def match(self, frame_received_at, now):
        if frame_received_at is None or now-frame_received_at > .5 or frame_received_at > now:
            raise ValueError('相机帧已过期，请重新采集')
        with self.lock:
            entries = list(self.entries)
        if not entries or now-entries[-1]['received_at'] > .5:
            raise ValueError('机器人位姿已过期')
        selected = min(entries, key=lambda e: abs(e['received_at']-frame_received_at))
        dt = abs(selected['received_at']-frame_received_at)*1000
        if dt > 80:
            raise ValueError('帧与位姿接收时间差超过 80 ms')
        window = [e for e in entries if now-.6 <= e['received_at'] <= now]
        if len(window) < 3 or window[-1]['received_at']-window[0]['received_at'] < .3:
            raise ValueError('机器人静止观测不足，请等待至少 0.3 秒')
        points = np.asarray([e['pose'] for e in window])
        reference = np.asarray(selected['pose'])
        position = np.max(np.linalg.norm(points[:,:3]-reference[:3],axis=1))
        qs = points[:,3:]/np.linalg.norm(points[:,3:],axis=1)[:,None]
        q = reference[3:]/np.linalg.norm(reference[3:])
        rotation = np.max(np.degrees(2*np.arccos(np.clip(np.abs(qs@q),0,1))))
        if position > .002 or rotation > 1.:
            raise ValueError('机器人未稳定，需停稳后采集')
        return selected, dt
