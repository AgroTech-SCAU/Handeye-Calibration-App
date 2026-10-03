import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import calibration_engine as engine

CONFIG = dict(type='charuco', squares_x=14, squares_y=9, square_size_mm=20.,
              marker_size_mm=15., dictionary='DICT_5X5_100', min_corners=6,
              legacy_pattern=False)
K = np.array([[900., 0., 640.], [0., 910., 480.], [0., 0., 1.]])
D = np.zeros(5)

def camera_file(folder):
    path = Path(folder)/'camera_intrinsics.yaml'
    path.write_text(yaml.safe_dump(dict(camera_matrix=dict(data=K.ravel().tolist()),
        distortion_coefficients=dict(data=D.tolist()),image_width=1280,image_height=960,
        created_at='test')),encoding='utf-8')
    return path

class BoardTests(unittest.TestCase):
    def setUp(self):
        import calibration_board as board
        self.module = board
        self.board = board.CalibrationBoard(CONFIG)

    def test_partial_rotated_ids_match_saved_geometry(self):
        image = self.board.board.generateImage((1400,900),marginSize=30)
        image[:,:600]=255
        a=self.board.detect(image)
        b=self.board.detect(cv2.rotate(image,cv2.ROTATE_180))
        self.assertGreaterEqual(len(a.ids),6)
        self.assertLess(len(a.ids),104)
        np.testing.assert_array_equal(a.ids,b.ids)
        np.testing.assert_allclose(b.image_points.reshape(-1,2),
            np.array([1399,899])-a.image_points.reshape(-1,2),atol=.25)
        data=dict(board_type='charuco',board=CONFIG)
        sample=dict(charuco_ids=a.ids.tolist(),corners_px=a.image_points.ravel().tolist())
        np.testing.assert_allclose(self.module.sample_object_points(data,sample),a.object_points)

    def test_even_row_legacy_geometry_roundtrip(self):
        for legacy in (False,True):
            board=self.module.CalibrationBoard(dict(CONFIG,squares_y=8,legacy_pattern=legacy))
            detection=board.detect(board.board.generateImage((1400,800),marginSize=30))
            sample=dict(charuco_ids=detection.ids.tolist(),corners_px=detection.image_points.ravel().tolist())
            np.testing.assert_allclose(self.module.sample_object_points(board.metadata(),sample),detection.object_points)

    def test_invalid_ids_are_rejected(self):
        data=self.board.metadata()
        for ids in ([0,0,2,3,4,5],[-1,1,2,3,4,5],[0,1,2,3,4,104],[0,1.5,2,3,4,5]):
            with self.subTest(ids=ids),self.assertRaises(ValueError):
                self.module.sample_object_points(data,dict(charuco_ids=ids,corners_px=[0.]*12))

    def test_rms_is_independent_of_point_count(self):
        for n in (6,88,104):
            self.assertAlmostEqual(self.module.reprojection_rms(np.zeros((n,2)),np.tile([.3,.4],(n,1))),.5)

    def test_pose_recovers_sparse_observation(self):
        obj=self.board.object_points[[0,3,9,14,28,50,70,95]]
        r=np.array([.2,-.3,.1]);t=np.array([-.12,-.07,.7])
        img=cv2.projectPoints(obj,r,t,K,D)[0]
        pose,error=self.module.solve_board_pose(obj,img,K,D)
        np.testing.assert_allclose(pose[:3,3],t,atol=1e-5)
        np.testing.assert_allclose(pose[:3,:3],cv2.Rodrigues(r)[0],atol=1e-4)
        self.assertLess(error,.001)

    def test_negative_depth_candidates_are_rejected(self):
        obj=self.board.object_points[[0,3,9,14,28,50,70,95]]
        img=cv2.projectPoints(obj,np.zeros(3),np.array([0.,0.,1.]),K,D)[0]
        with mock.patch.object(cv2,'solvePnPGeneric',return_value=(1,[np.zeros((3,1))],[np.array([[0.],[0.],[-1.]])],None)):
            with self.assertRaises(ValueError):
                self.module.solve_board_pose(obj,img,K,D)

class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=camera_file(self.tmp.name)
        self.frame=np.zeros((960,1280,3),np.uint8)
        obj=engine.object_points(11,8,15)
        self.corners=cv2.projectPoints(obj,np.array([.2,-.1,.05]),np.array([-.07,-.04,.6]),K,D)[0]
        self.detector=mock.patch.object(engine,'detect_chessboard',return_value=(True,self.corners))
        self.detector.start()
    def tearDown(self):self.detector.stop();self.tmp.cleanup()
    def add(self,session,path=None,square=15,frame=None):
        return session.add(self.frame if frame is None else frame,[0,0,0,0,0,0,1],path or self.path,
            11,8,square,'pose',quality_mode='minimal')
    def test_handeye_locks_board(self):
        s=engine.HandEyeCollection();self.add(s)
        with self.assertRaises(ValueError):self.add(s,square=20)
        self.assertEqual(len(s.samples),1)
    def test_handeye_locks_intrinsics(self):
        s=engine.HandEyeCollection();self.add(s)
        data=yaml.safe_load(self.path.read_text());data['camera_matrix']['data'][0]=1000
        self.path.write_text(yaml.safe_dump(data))
        with self.assertRaises(ValueError):self.add(s)
        with self.assertRaises(ValueError):s.save(Path(self.tmp.name)/'samples.yaml',self.path,11,8,15)
    def test_resolution_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):self.add(engine.HandEyeCollection(),frame=self.frame[:480,:640])
    def test_intrinsic_locks_board_and_resolution(self):
        s=engine.IntrinsicCalibration();s.add(self.frame,11,8,15,'minimal')
        with self.assertRaises(ValueError):s.add(self.frame,11,8,20,'minimal')
        with self.assertRaises(ValueError):s.add(self.frame[:480,:640],11,8,15,'minimal')
    def test_saved_intrinsics_are_collection_snapshot(self):
        s=engine.HandEyeCollection();self.add(s)
        out=Path(self.tmp.name)/'samples.yaml';s.save(out,self.path,11,8,15)
        data=yaml.safe_load(out.read_text())
        self.assertEqual(data['schema_version'],2)
        self.assertEqual(data['reprojection_error_definition'],'point_rms_2d')
        self.assertEqual(data['image_size_at_collection'],[1280,960])

if __name__=='__main__':unittest.main()

class BATests(unittest.TestCase):
    def test_variable_point_ba_recovers_known_handeye_with_bound_intrinsics(self):
        sys.path.insert(0,str(ROOT/'algorithms'))
        from bundle_adjust import run_bundle_adjustment
        from calibration_board import CalibrationBoard
        board=CalibrationBoard(CONFIG)
        X=np.eye(4);X[:3,:3]=cv2.Rodrigues(np.array([.1,-.05,.03]))[0];X[:3,3]=[.03,-.02,.04]
        Y=np.eye(4);Y[:3,3]=[-.1,-.05,.8]
        samples=[]
        for i in range(12):
            A=np.eye(4);A[:3,:3]=cv2.Rodrigues(np.array([.15*np.sin(i),.2*np.cos(i),.1*np.sin(i*.7)]))[0]
            A[:3,3]=[.03*np.sin(i),.02*np.cos(i),.01*np.sin(i*.4)]
            B=np.linalg.inv(X)@np.linalg.inv(A)@Y
            ids=np.arange(i%8,104,1+i%3,dtype=int)
            corners=cv2.projectPoints(board.object_points[ids],cv2.Rodrigues(B[:3,:3])[0],B[:3,3],K,D)[0]
            samples.append(dict(gripper_in_base=A.tolist(),target_to_camera=B.tolist(),charuco_ids=ids.tolist(),corners_px=corners.ravel().tolist(),reprojection_error_px=.01))
        data=dict(board.metadata(),handeye_mode='eye_in_hand',samples=samples,
            camera_matrix_at_collection=dict(data=K.ravel().tolist()),distortion_at_collection=dict(data=D.tolist()),image_size_at_collection=[1280,960])
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'samples.yaml';p.write_text(yaml.safe_dump(data))
            init=X.copy();init[:3,3]+=[.003,-.002,.001]
            result=run_bundle_adjustment(p,X_init=init,verbose=False)
            self.assertIsNotNone(result)
            np.testing.assert_allclose(result[0],X,atol=2e-5)
            self.assertLess(result[2]['ba_reprojection_rms_px'],.001)
            from algorithm_runner import run_algorithm
            log=[]
            self.assertEqual(run_algorithm('solve',p,'ba',log.append),0,''.join(log))
            solved=yaml.safe_load(p.with_name('samples_result.yaml').read_text())
            self.assertTrue(solved['ba_refined'])
            np.testing.assert_allclose(solved['transform_matrix'],X,atol=2e-5)
            bad=camera_file(folder);wrong=yaml.safe_load(bad.read_text());wrong['camera_matrix']['data'][0]=1200
            bad.write_text(yaml.safe_dump(wrong))
            with self.assertRaises(ValueError):run_bundle_adjustment(p,X_init=init,intrinsics_path=bad,verbose=False)

class IntrinsicCharucoTests(unittest.TestCase):
    def test_variable_point_intrinsics_recovers_camera(self):
        from calibration_board import CalibrationBoard,Detection
        board=CalibrationBoard(CONFIG)
        session=engine.IntrinsicCalibration()
        frame=np.zeros((960,1280,3),np.uint8)
        for i in range(15):
            ids=np.arange(i%5,104,1+i%2)
            obj=board.object_points[ids]
            r=np.array([.4*np.sin(i),.35*np.cos(i),.15*np.sin(i*.4)])
            t=np.array([-.14+.1*np.sin(i*.8),-.09+.08*np.cos(i*.5),.5+.2*(i%3)])
            img=cv2.projectPoints(obj,r,t,K,D)[0]
            with mock.patch.object(CalibrationBoard,'detect',return_value=Detection(obj,img,ids)):
                session.add(frame,11,8,20,'minimal',board=CONFIG)
        with tempfile.TemporaryDirectory() as folder:
            result=session.solve(Path(folder)/'intrinsics.yaml',11,8,20,'minimal',board=CONFIG)
            recovered=np.asarray(result['camera_matrix']['data']).reshape(3,3)
            np.testing.assert_allclose(recovered,K,atol=.05)
            self.assertLess(result['reprojection_error_px'],.001)
            self.assertEqual(result['board_type'],'charuco')
