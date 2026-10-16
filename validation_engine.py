"""Independent Eye-in-Hand consistency validation against a frozen calibration

Validation never estimates or modifies the hand-eye transform
The fixed board reference is determined from the training observations only
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import yaml
from scipy.spatial.transform import Rotation

from calibration_board import CalibrationBoard, sample_object_points


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str,
                                     separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def sample_signature(sample):
    # Do not use mutable user-facing IDs to determine train/validation independence
    return digest({name: np.asarray(sample[name], dtype=float).round(8).tolist()
                   for name in ('gripper_in_base', 'target_to_camera')})


def valid_transform(value, label):
    matrix = np.asarray(value, dtype=np.float64)
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise ValueError(f'{label} 必须是有限的 4×4 矩阵')
    if not np.allclose(matrix[3], [0, 0, 0, 1], atol=1e-7):
        raise ValueError(f'{label} 最后一行无效')
    r = matrix[:3, :3]
    if not np.allclose(r.T @ r, np.eye(3), atol=1e-3) or np.linalg.det(r) < 0.99:
        raise ValueError(f'{label} 旋转矩阵无效')
    return matrix


def inv(t):
    out = np.eye(4)
    out[:3, :3] = t[:3, :3].T
    out[:3, 3] = -out[:3, :3] @ t[:3, 3]
    return out


def mean_pose(poses):
    if not poses:
        raise ValueError('缺少用于建立棋盘参考的数据')
    result = np.eye(4)
    result[:3, 3] = np.mean([p[:3, 3] for p in poses], axis=0)
    quats = Rotation.from_matrix([p[:3, :3] for p in poses])
    result[:3, :3] = quats.mean().as_matrix()
    return result


def _intrinsics(metadata):
    k = metadata.get('camera_matrix_at_collection')
    d = metadata.get('distortion_at_collection')
    sz = metadata.get('image_size_at_collection')
    if not isinstance(k, dict) or not isinstance(d, dict) or not isinstance(sz, (list, tuple)) or len(sz) != 2:
        raise ValueError('样本缺少采集时冻结的相机内参')
    matrix = np.asarray(k['data'], dtype=float).reshape(3, 3)
    distortion = np.asarray(d['data'], dtype=float).reshape(-1)
    size = [int(sz[0]), int(sz[1])]
    if not np.isfinite(matrix).all() or not np.isfinite(distortion).all() or matrix[0, 0] <= 0 or matrix[1, 1] <= 0:
        raise ValueError('相机内参不合法')
    return matrix, distortion, size


def freeze_solution(training_path: Path, result_path: Path, output_path: Path):
    training_path, result_path = Path(training_path), Path(result_path)
    data = yaml.safe_load(training_path.read_text(encoding='utf-8')) or {}
    result = yaml.safe_load(result_path.read_text(encoding='utf-8')) or {}
    if data.get('handeye_mode') != 'eye_in_hand':
        raise ValueError('目前只支持 Eye-in-Hand 验证')
    frames = {key: str(data.get(key, '')) for key in ('robot_base_frame', 'robot_end_frame', 'camera_frame')}
    if any(not frame or frame.startswith('UNRESOLVED_') for frame in frames.values()):
        raise ValueError('训练样本坐标系不完整')
    if (result.get('parent_frame'), result.get('child_frame')) != (frames['robot_end_frame'], frames['camera_frame']):
        raise ValueError('结果矩阵与训练样本的末端或相机坐标系不一致')
    if not str(result.get('stored_transform_convention', '')).startswith('camera_to_gripper'):
        raise ValueError('结果矩阵缺少明确的末端到相机变换约定')
    x = valid_transform(result.get('transform_matrix'), '手眼矩阵')
    matrix, distortion, size = _intrinsics(data)
    board = data.get('board')
    if not isinstance(board, dict):
        raise ValueError('训练样本缺少棋盘规格')
    CalibrationBoard(board)
    samples = data.get('samples') or []
    if len(samples) < 3:
        raise ValueError('训练数据不足')
    signatures = [sample_signature(s) for s in samples]
    if len(set(signatures)) != len(signatures):
        raise ValueError('训练样本中存在重复位姿记录，请先清洗')
    removed = {int(i) for i in result.get('removed_samples', []) if str(i).isdigit()}
    selected = [s for i, s in enumerate(samples, 1) if i not in removed]
    if len(selected) < 3:
        selected = samples
    poses = [valid_transform(s['gripper_in_base'], '机器人位姿') @ x @
             valid_transform(s['target_to_camera'], '棋盘位姿') for s in selected]
    reference = mean_pose(poses)
    fixed = {
        'kind': 'eye_in_hand_frozen_reference',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'robot_base_frame': frames['robot_base_frame'],
        'robot_end_frame': frames['robot_end_frame'],
        'camera_frame': frames['camera_frame'],
        'board': board,
        'camera_matrix_at_collection': data['camera_matrix_at_collection'],
        'distortion_at_collection': data['distortion_at_collection'],
        'image_size_at_collection': size,
        'handeye_transform': x.tolist(),
        'board_reference_in_base': reference.tolist(),
        'training_sample_signatures': signatures,
        'training_sample_count': len(samples),
        'training_file_sha256': hashlib.sha256(training_path.read_bytes()).hexdigest(),
        'result_file_sha256': hashlib.sha256(result_path.read_bytes()).hexdigest(),
        'training_sample_path': str(training_path),
        'result_path': str(result_path),
        'reference_note': '棋盘参考由训练样本建立，不是独立测量真值',
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix('.tmp')
    tmp.write_text(yaml.safe_dump(fixed, sort_keys=False, allow_unicode=True), encoding='utf-8')
    tmp.replace(output_path)
    return fixed


def load_frozen(path: Path, check_sources=True):
    fixed = yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}
    if fixed.get('kind') != 'eye_in_hand_frozen_reference':
        raise ValueError('缺少固定手眼矩阵及训练棋盘参考')
    valid_transform(fixed['handeye_transform'], '固定手眼矩阵')
    valid_transform(fixed['board_reference_in_base'], '固定棋盘参考')
    if check_sources:
        for source_key, sha_key in (('training_sample_path', 'training_file_sha256'),
                                    ('result_path', 'result_file_sha256')):
            source = Path(fixed[source_key])
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != fixed[sha_key]:
                raise ValueError('训练样本或手眼结果已经变化，请重新冻结矩阵')
    return fixed


def validate_metadata(fixed, data):
    if data.get('handeye_mode') != 'eye_in_hand':
        raise ValueError('验证样本不是 Eye-in-Hand 数据')
    for name in ('robot_base_frame', 'robot_end_frame', 'camera_frame'):
        if str(data.get(name, '')) != fixed[name]:
            raise ValueError(f'验证样本坐标系 {name} 不匹配')
    if data.get('board') != fixed['board']:
        raise ValueError('验证棋盘参数与训练时不同')
    k, d, size = _intrinsics(data)
    base_k, base_d, base_size = _intrinsics(fixed)
    if size != base_size or k.shape != base_k.shape or d.shape != base_d.shape or not np.allclose(k, base_k, atol=1e-8, rtol=0) or not np.allclose(d, base_d, atol=1e-8, rtol=0):
        raise ValueError('验证相机内参与训练时不一致')


def evaluate_sample(fixed, sample, metadata):
    object_points = sample_object_points(metadata, sample).astype(np.float64)
    observed = np.asarray(sample['corners_px'], dtype=float).reshape(-1, 2)
    bte = valid_transform(sample['gripper_in_base'], '验证机械臂位姿')
    ctp = valid_transform(sample['target_to_camera'], '验证棋盘位姿')
    x = valid_transform(fixed['handeye_transform'], '手眼矩阵')
    reference = valid_transform(fixed['board_reference_in_base'], '棋盘参考')
    btp = bte @ x @ ctp
    delta = inv(reference) @ btp
    trans_mm = float(np.linalg.norm(delta[:3, 3]) * 1000)
    angle_deg = float(np.rad2deg(Rotation.from_matrix(delta[:3, :3]).magnitude()))
    prediction = inv(bte @ x) @ reference
    if np.min((object_points @ prediction[:3, :3].T + prediction[:3, 3])[:, 2]) <= 0:
        raise ValueError('预测角点位于相机后方，检查 Frame 或固定标定板是否移动')
    k, d, _ = _intrinsics(fixed)
    rvec, _ = cv2.Rodrigues(prediction[:3, :3])
    projected, _ = cv2.projectPoints(object_points, rvec, prediction[:3, 3], k, d)
    projected = projected.reshape(-1, 2)
    reproj = np.linalg.norm(projected - observed, axis=1)
    return {
        'id': int(sample['id']), 'translation_error_mm': trans_mm,
        'rotation_error_deg': angle_deg,
        'prediction_reprojection_rms_px': float(np.sqrt(np.mean(reproj ** 2))),
        'prediction_reprojection_p95_px': float(np.percentile(reproj, 95)),
        'detected_reprojection_rms_px': float(sample.get('reprojection_error_px', 0)),
        'observed_px': observed.tolist(), 'predicted_px': projected.tolist(),
        'captured_at': sample.get('captured_at', ''),
    }


def evaluate_dataset(fixed, data, mode='offline', thresholds=None):
    validate_metadata(fixed, data)
    samples = data.get('samples')
    if not isinstance(samples, list) or not samples:
        raise ValueError('验证文件没有样本')
    used = set(fixed['training_sample_signatures'])
    signatures = [sample_signature(s) for s in samples]
    if any(s in used for s in signatures):
        raise ValueError('验证数据包含参与求解的训练样本，不允许作为独立验证')
    if len(set(signatures)) != len(signatures):
        raise ValueError('验证样本内部存在重复记录')
    rows = [evaluate_sample(fixed, sample, data) for sample in samples]
    summary = {'count': len(rows)}
    for field, prefix in [('translation_error_mm', 'translation_mm'),
                          ('rotation_error_deg', 'rotation_deg'),
                          ('prediction_reprojection_rms_px', 'projection_px')]:
        v = np.array([r[field] for r in rows], dtype=float)
        summary.update({f'{prefix}_rms': float(np.sqrt(np.mean(v*v))),
                        f'{prefix}_p95': float(np.percentile(v, 95)),
                        f'{prefix}_max': float(np.max(v))})
    # Thresholds are a configurable engineering acceptance policy, not accuracy certification
    limits = dict(translation_rms_mm=5., rotation_rms_deg=1., projection_rms_px=4.)
    if thresholds is not None:
        if not isinstance(thresholds, dict) or set(thresholds) != set(limits):
            raise ValueError('工程验收阈值字段不完整')
        for key in limits:
            value = float(thresholds[key])
            if not np.isfinite(value) or value <= 0:
                raise ValueError('工程验收阈值必须为有限正数')
            limits[key] = value
    status = 'insufficient' if len(rows) < 5 else 'pass' if (summary['translation_mm_rms'] <= limits['translation_rms_mm'] and
          summary['rotation_deg_rms'] <= limits['rotation_rms_deg'] and summary['projection_px_rms'] <= limits['projection_rms_px']) else 'fail'
    return dict(kind='independent_eye_in_hand_validation', mode=mode, status=status,
                created_at=datetime.now(timezone.utc).isoformat(),
                robot_base_frame=fixed['robot_base_frame'], robot_end_frame=fixed['robot_end_frame'], camera_frame=fixed['camera_frame'],
                fixed_reference_sha256=digest(fixed), metrics=summary, thresholds=limits,
                samples=rows, warnings=['本结果评估固定标定板的一致性与投影偏差，不代表绝对空间定位精度',
                   '验证数据应在独立的采集会话中获得，且标定板不可相对基座移动'])


def run_validation(reference_path, samples_path, report_path, mode='offline', thresholds=None):
    fixed = load_frozen(Path(reference_path))
    doc = yaml.safe_load(Path(samples_path).read_text(encoding='utf-8')) or {}
    report = evaluate_dataset(fixed, doc, mode, thresholds)
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(yaml.safe_dump(report, sort_keys=False, allow_unicode=True), encoding='utf-8')
    tmp.replace(path)
    return report


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--reference', required=True)
    p.add_argument('--samples', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--mode', choices=('offline', 'live'), default='offline')
    p.add_argument('--thresholds', default='')
    args = p.parse_args()
    report = run_validation(args.reference, args.samples, args.report, args.mode,
                            json.loads(args.thresholds) if args.thresholds else None)
    print('HANDEYE_JOB_RESULT:' + json.dumps(report, ensure_ascii=False))
