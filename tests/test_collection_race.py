import importlib.util
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest import mock
import numpy as np
import cv2
import yaml
from calibration_board import CalibrationBoard,Detection

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('test_bridge_impl',ROOT/'backend/bridge.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class RaceTests(unittest.TestCase):
    def test_config_cannot_interleave_first_capture(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ,{'HANDEYE_MOCK':'1','HANDEYE_DATA_DIR':folder}), mock.patch.object(module.Bridge,'_emit',return_value=None):
            bridge=module.Bridge()
            try:
                out=Path(folder)/'output';out.mkdir(exist_ok=True)
                K=np.array([[600.,0,320],[0,600,240],[0,0,1.]])
                (out/'camera_intrinsics.yaml').write_text(yaml.safe_dump(dict(camera_matrix=dict(data=K.ravel().tolist()),distortion_coefficients=dict(data=[0.]*5),image_width=640,image_height=480)))
                bridge.current_frame=np.zeros((480,640,3),np.uint8);bridge.frame_received_at=time.monotonic()
                board=CalibrationBoard(bridge.config.board_config());obj=board.object_points
                corners=cv2.projectPoints(obj,np.array([.1,.2,0.]),np.array([-.07,-.04,.6]),K,np.zeros(5))[0]
                entered=threading.Event();release=threading.Event();changed=[];errors=[]
                def slow_detect(*args,**kwargs):
                    entered.set();release.wait(2);return Detection(obj,corners,None)
                def capture():
                    try:bridge.capture_handeye(dict(mode='manual',manual_type='quaternion',values=[0,0,0,0,0,0,1],quality_mode='minimal'))
                    except Exception as e:errors.append(e)
                def configure():
                    try:bridge._apply_config(dict(square_size_mm=20));changed.append(True)
                    except ValueError:changed.append(False)
                with mock.patch.object(CalibrationBoard,'detect',side_effect=slow_detect):
                    a=threading.Thread(target=capture);a.start();self.assertTrue(entered.wait(2))
                    b=threading.Thread(target=configure);b.start();time.sleep(.05);release.set();a.join(3);b.join(3)
                self.assertFalse(a.is_alive());self.assertFalse(b.is_alive());self.assertEqual(errors,[])
                self.assertEqual(changed,[False]);self.assertEqual(len(bridge.handeye.samples),1)
                self.assertEqual(bridge.config.square_size_mm,bridge.handeye.board_spec['square_size_mm'])
                self.assertTrue(bridge.save_samples({})['path'])
            finally:bridge.shutdown()
