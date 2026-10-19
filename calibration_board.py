"""Shared board geometry, ID correspondence and per-corner pixel RMS"""
from __future__ import annotations
from dataclasses import dataclass
import cv2
import numpy as np


def reprojection_rms(observed, projected):
    a = np.asarray(observed, dtype=np.float64).reshape(-1, 2)
    b = np.asarray(projected, dtype=np.float64).reshape(-1, 2)
    if a.shape != b.shape or not len(a) or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('角点数量或坐标无效')
    return float(np.sqrt(np.mean(np.sum((a-b)**2, axis=1))))


def positive_int(value, name, minimum=1):
    if isinstance(value, bool) or not np.isfinite(float(value)) or int(value) != float(value) or int(value) < minimum:
        raise ValueError(name + ' 必须是有效正整数')
    return int(value)


@dataclass(frozen=True)
class Detection:
    object_points: np.ndarray
    image_points: np.ndarray
    ids: np.ndarray | None


class CalibrationBoard:
    def __init__(self, config):
        self.kind = config.get('type', 'chessboard')
        square = float(config['square_size_mm'])
        if not np.isfinite(square) or square <= 0:
            raise ValueError('方格尺寸必须是有限正数')
        self.config = dict(type=self.kind, square_size_mm=square)
        self.board = None
        if self.kind == 'chessboard':
            cols = positive_int(config['cols'], 'cols', 2)
            rows = positive_int(config['rows'], 'rows', 2)
            self.config.update(cols=cols, rows=rows)
            self.pattern = (cols, rows)
            self.object_points = np.zeros((cols*rows, 3), np.float32)
            self.object_points[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)
            self.object_points *= square/1000.
            self.min_corners = cols*rows
        elif self.kind == 'charuco':
            aruco = getattr(cv2, 'aruco', None)
            if aruco is None or not hasattr(aruco, 'CharucoDetector'):
                raise ValueError('CharUco 需要支持 CharucoDetector 的 OpenCV 4.8+')
            sx = positive_int(config['squares_x'], 'squares_x', 3)
            sy = positive_int(config['squares_y'], 'squares_y', 3)
            marker = float(config['marker_size_mm'])
            dictionary = config['dictionary']
            if not np.isfinite(marker) or not 0 < marker < square:
                raise ValueError('Marker 尺寸必须大于 0 且小于方格尺寸')
            if not isinstance(dictionary, str) or not dictionary.startswith('DICT_') or not hasattr(aruco, dictionary):
                raise ValueError('无效 ArUco 字典')
            pattern = config.get('legacy_pattern', False)
            if not isinstance(pattern, bool):
                raise ValueError('legacy_pattern 必须是布尔值')
            self.min_corners = positive_int(config.get('min_corners', 6), 'min_corners', 4)
            if self.min_corners > (sx-1)*(sy-1):
                raise ValueError('最少角点数超过标定板容量')
            d = aruco.getPredefinedDictionary(getattr(aruco, dictionary))
            if (sx*sy)//2 > len(d.bytesList):
                raise ValueError('ArUco 字典容量不足')
            self.board = aruco.CharucoBoard((sx, sy), square/1000., marker/1000., d)
            self.board.setLegacyPattern(pattern)
            self.config.update(squares_x=sx, squares_y=sy, marker_size_mm=marker,
                dictionary=dictionary, min_corners=self.min_corners, legacy_pattern=pattern)
            self.object_points = np.asarray(self.board.getChessboardCorners(), np.float32)
            self.pattern = (sx-1, sy-1)
        else:
            raise ValueError('未知标定板类型')

    def metadata(self):
        result = dict(board_type=self.kind, board=dict(self.config), square_size_mm=self.config['square_size_mm'])
        if self.kind == 'chessboard':
            result['chessboard'] = '%dx%d' % self.pattern
        return result

    def detect(self, gray, matrix=None, distortion=None):
        if self.kind == 'chessboard':
            from calibration_engine import detect_chessboard
            ok, corners = detect_chessboard(gray, self.pattern)
            if not ok:
                raise ValueError('当前画面未检测到完整棋盘格')
            return Detection(self.object_points.copy(), corners, None)
        params = cv2.aruco.CharucoParameters()
        if matrix is not None:
            params.cameraMatrix = matrix
            params.distCoeffs = distortion
        detector = cv2.aruco.CharucoDetector(self.board, params)
        corners, ids, _, _ = detector.detectBoard(gray)
        if ids is None or len(ids) < self.min_corners:
            raise ValueError('CharUco 有效角点不足')
        order = np.argsort(ids.ravel())
        ids = ids.ravel()[order].astype(np.int32)
        corners = np.asarray(corners, np.float32).reshape(-1, 1, 2)[order]
        points = corners.reshape(-1,2)
        spacing = np.linalg.norm(points[:,None]-points[None,:],axis=2)
        np.fill_diagonal(spacing,np.inf)
        half = max(1,min(5,int(np.min(spacing)*.25)))
        corners = cv2.cornerSubPix(gray,corners.copy(),(half,half),(-1,-1),
            (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,40,1e-4))
        obj, img = self.board.matchImagePoints(corners, ids.reshape(-1, 1))
        obj = np.asarray(obj, np.float32).reshape(-1, 3)
        img = np.asarray(img, np.float32).reshape(-1, 1, 2)
        validate_geometry(obj, img)
        return Detection(obj, img, ids)

    def draw(self, image, detection):
        if self.kind == 'chessboard':
            cv2.drawChessboardCorners(image, self.pattern, detection.image_points, True)
        else:
            cv2.aruco.drawDetectedCornersCharuco(image, detection.image_points, detection.ids.reshape(-1, 1))


def validate_geometry(obj, img):
    obj = np.asarray(obj, np.float64).reshape(-1, 3)
    img = np.asarray(img, np.float64).reshape(-1, 2)
    if len(obj) < 4 or len(obj) != len(img) or not np.isfinite(obj).all() or not np.isfinite(img).all():
        raise ValueError('无效角点坐标或数量')
    if np.linalg.matrix_rank(obj-obj.mean(0)) < 2 or np.linalg.matrix_rank(img-img.mean(0)) < 2:
        raise ValueError('角点共线，无法估计姿态')
    distances = np.linalg.norm(img[:, None]-img[None, :], axis=2)
    np.fill_diagonal(distances, np.inf)
    if np.min(distances) < 3:
        raise ValueError('角点像素间距过小')


def sample_object_points(data, sample):
    kind = data.get('board_type', data.get('board', {}).get('type', 'chessboard'))
    config = data.get('board')
    if config is None:
        cols, rows = map(int, data.get('chessboard', '11x8').split('x'))
        config = dict(type=kind, cols=cols, rows=rows, square_size_mm=data.get('square_size_mm', 15))
    if config.get('type') != kind:
        raise ValueError('标定板类型与元数据不一致')
    board = CalibrationBoard(config)
    obj = board.object_points
    img = np.asarray(sample['corners_px'], np.float64).reshape(-1, 2)
    if kind == 'charuco':
        raw = np.asarray(sample['charuco_ids'])
        if raw.ndim != 1 or raw.dtype.kind not in 'iuf' or not np.isfinite(raw).all():
            raise ValueError('无效 CharUco ID')
        ids = raw.astype(np.int64)
        if not np.array_equal(raw, ids) or len(np.unique(ids)) != len(ids) or np.any(ids < 0) or np.any(ids >= len(obj)) or len(ids) < board.min_corners:
            raise ValueError('CharUco ID 重复、越界或数量不足')
        obj = obj[ids]
    validate_geometry(obj, img)
    return obj.copy()


def solve_board_pose(obj, img, matrix, distortion):
    obj = np.ascontiguousarray(obj, dtype=np.float64).reshape(-1, 3)
    img = np.ascontiguousarray(img, dtype=np.float64).reshape(-1, 1, 2)
    validate_geometry(obj, img)
    candidates = []
    for method in (cv2.SOLVEPNP_IPPE, cv2.SOLVEPNP_SQPNP, cv2.SOLVEPNP_ITERATIVE):
        try:
            result = cv2.solvePnPGeneric(obj, img, matrix, distortion, flags=method)
        except cv2.error:
            continue
        if not result[0]:
            continue
        for r, t in zip(result[1], result[2]):
            r = np.asarray(r, np.float64).reshape(3, 1).copy()
            t = np.asarray(t, np.float64).reshape(3, 1).copy()
            if not np.isfinite(r).all() or not np.isfinite(t).all():
                continue
            R = cv2.Rodrigues(r)[0]
            if np.min((obj@R.T+t.ravel())[:, 2]) <= 0:
                continue
            error = reprojection_rms(img, cv2.projectPoints(obj, r, t, matrix, distortion)[0])
            try:
                rr, tt = cv2.solvePnPRefineLM(obj, img, matrix, distortion, r.copy(), t.copy())
                RR = cv2.Rodrigues(rr)[0]
                refined = reprojection_rms(img, cv2.projectPoints(obj, rr, tt, matrix, distortion)[0])
                if np.isfinite(rr).all() and np.isfinite(tt).all() and np.min((obj@RR.T+tt.ravel())[:,2]) > 0 and refined <= error:
                    r, t, R, error = rr, tt, RR, refined
            except cv2.error:
                pass
            candidates.append((error, R, t))
    if not candidates:
        raise ValueError('PnP 无有效正深度解')
    candidates.sort(key=lambda c: c[0])
    error, rotation, translation = candidates[0]
    for other_error, other_rotation, _ in candidates[1:]:
        angle = np.degrees(np.arccos(np.clip((np.trace(rotation.T@other_rotation)-1)/2, -1, 1)))
        if error > .05 and other_error-error < max(.05, error*.1) and angle > 10:
            raise ValueError('平面姿态存在近似等误差双解，请增大倾斜或角点覆盖')
    pose = np.eye(4)
    pose[:3,:3] = rotation
    pose[:3,3] = translation.ravel()
    return pose, error
