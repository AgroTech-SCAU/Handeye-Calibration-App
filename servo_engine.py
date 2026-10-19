"""Read-only RGB-D geometry and guarded target association for discrete visual servoing

Robot actuation is provided by ros_motion.py, never by this module
"""
from __future__ import annotations
import math
import cv2
import numpy as np


def decode_depth_image(msg):
    """Decode ROS2 depth to metres, preserving row stride and endianness"""
    encoding = str(msg.encoding).upper()
    if encoding not in ('16UC1', 'MONO16', '32FC1'):
        raise ValueError('深度话题必须发布 16UC1 / mono16 (mm) 或 32FC1 (m)')
    dtype = np.dtype('>f4' if encoding == '32FC1' and msg.is_bigendian else
                     '<f4' if encoding == '32FC1' else
                     '>u2' if msg.is_bigendian else '<u2')
    width, height, step = int(msg.width), int(msg.height), int(msg.step)
    if width <= 0 or height <= 0 or step < width * dtype.itemsize or len(msg.data) < height * step:
        raise ValueError('ROS2 深度图的尺寸或 row stride 不合法')
    raw = np.frombuffer(msg.data, dtype=np.uint8, count=height * step).reshape(height, step)
    depth = np.ndarray((height, width), dtype=dtype, buffer=raw, strides=(step, dtype.itemsize)).astype(np.float32, copy=True)
    if encoding != '32FC1':
        depth *= 0.001
    depth[~np.isfinite(depth) | (depth <= 0)] = np.nan
    return depth


def depth_at(depth, x, y, window=5, min_z=0.12, max_z=2.5):
    height, width = depth.shape
    x, y = int(round(x)), int(round(y))
    if x < 0 or x >= width or y < 0 or y >= height:
        raise ValueError('选择的位置超出深度图')
    radius = max(1, min(7, int(window)))
    roi = depth[max(0,y-radius):min(height,y+radius+1), max(0,x-radius):min(width,x+radius+1)]
    good = roi[np.isfinite(roi) & (roi >= min_z) & (roi <= max_z)]
    if len(good) < max(5, int(roi.size * .30)):
        raise ValueError('该目标附近有效深度不足，尝试重新框选无遮挡区域')
    depth_m = float(np.median(good))
    if float(np.quantile(good,.90)-np.quantile(good,.10)) > max(.035, depth_m * .045):
        raise ValueError('目标深度变化过大，可能跨越背景或遮挡边缘')
    return depth_m


def pixel_to_point(u,v,z,k,dist=None):
    k = np.asarray(k,dtype=float).reshape(3,3)
    d = np.asarray(dist if dist is not None else [],dtype=float).reshape(-1)
    if not np.isfinite(k).all() or k[0,0]<=0 or k[1,1]<=0 or not np.isfinite([u,v,z]).all() or z<=0:
        raise ValueError('无效 RGB-D 内参或三维目标')
    uv = cv2.undistortPoints(np.array([[[float(u),float(v)]]],np.float64),k,d if len(d) else None).reshape(2)
    return np.array([float(uv[0])*z,float(uv[1])*z,z],dtype=float)


def camera_to_base(point, base_end, end_camera):
    point=np.asarray(point,dtype=float)
    if point.shape!=(3,) or not np.isfinite(point).all():
        raise ValueError('相机点坐标不合法')
    matrix=np.asarray(base_end,dtype=float)@np.asarray(end_camera,dtype=float)
    if matrix.shape!=(4,4) or not np.isfinite(matrix).all():
        raise ValueError('当前手眼或机械臂变换无效')
    return (matrix@np.array([*point,1.]))[:3]


def project_base(point_base, base_end, end_camera, k,dist=None):
    camera_base = np.linalg.inv(np.asarray(base_end)@np.asarray(end_camera))
    cam=(camera_base@np.array([*point_base,1.]))[:3]
    if cam[2]<=.08:
        raise ValueError('目标已不在相机前方')
    uv,_=cv2.projectPoints(cam.reshape(1,1,3), np.zeros(3),np.zeros(3), np.asarray(k).reshape(3,3),np.asarray(dist if dist is not None else []))
    return uv.reshape(2)


def make_template(frame,u,v,radius=16):
    height,width=frame.shape[:2]
    x,y=int(round(u)),int(round(v))
    r=max(8,min(32,int(radius)))
    if x-r<0 or y-r<0 or x+r>=width or y+r>=height:
        raise ValueError('目标离图像边缘太近，无法安全跟踪')
    patch=cv2.cvtColor(frame[y-r:y+r+1,x-r:x+r+1],cv2.COLOR_BGR2GRAY)
    if float(patch.std())<9.:
        raise ValueError('所选目标缺少可跟踪纹理，请选择边缘或明显特征点')
    return patch


def track_template(frame,template, predicted_u,predicted_v,search_radius=55,min_score=.76):
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    h,w=gray.shape; th,tw=template.shape
    x,y=float(predicted_u),float(predicted_v)
    radius=min(max(20,int(search_radius)),100)
    x0=max(0,int(x-radius-tw//2));x1=min(w,int(x+radius+tw//2+1))
    y0=max(0,int(y-radius-th//2));y1=min(h,int(y+radius+th//2+1))
    crop=gray[y0:y1,x0:x1]
    if crop.shape[0]<th or crop.shape[1]<tw:
        raise ValueError('目标投影到图像边缘，跟踪已停止')
    scoremap=cv2.matchTemplate(crop,template,cv2.TM_CCOEFF_NORMED)
    _,score,_,pos=cv2.minMaxLoc(scoremap)
    if not np.isfinite(score) or score<min_score:
        raise ValueError('目标跟踪置信度不足，已停止后续机械臂运动')
    u=x0+pos[0]+tw/2;v=y0+pos[1]+th/2
    if math.hypot(u-x,v-y)>radius:
        raise ValueError('目标跟踪偏离预测范围')
    return u,v,float(score)


def limited_step(tip_xyz, target_xyz, step_m=.02, clearance_m=.03):
    current=np.asarray(tip_xyz,float).reshape(3)
    target=np.asarray(target_xyz,float).reshape(3)
    delta=target-current
    distance=float(np.linalg.norm(delta))
    if not np.isfinite(distance):raise ValueError('目标距离不是有限值')
    if distance<=clearance_m:return current.copy(),distance,True
    move=min(float(step_m),distance-float(clearance_m))
    if move<=0 or move>.05:raise ValueError('单步运动距离超过安全限制')
    return current+(delta/distance)*move,distance,False
