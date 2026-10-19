"""URDF kinematics for hand-eye verification without publishing ROS TF.

A URDF is a geometric model, not a source of robot state.  Only a path made
of fixed joints may be resolved without accompanying joint positions.
"""
from __future__ import annotations

import math
import subprocess
import xml.etree.ElementTree as ET
from collections import deque
from pathlib import Path

import numpy as np


def _matrix_xyz_rpy(xyz: str, rpy: str) -> np.ndarray:
    t = np.fromstring(xyz, sep=' ', dtype=float)
    angles = np.fromstring(rpy, sep=' ', dtype=float)
    if len(t) != 3 or len(angles) != 3 or not np.isfinite(t).all() or not np.isfinite(angles).all():
        raise ValueError('URDF origin 必须包含有限的 xyz/rpy 各三个数值')
    a, b, c = angles
    ca,sa,cb,sb,cc,sc=math.cos(a),math.sin(a),math.cos(b),math.sin(b),math.cos(c),math.sin(c)
    rot=np.array([[cc*cb,cc*sb*sa-sc*ca,cc*sb*ca+sc*sa],
                  [sc*cb,sc*sb*sa+cc*ca,sc*sb*ca-cc*sa],[-sb,cb*sa,cb*ca]],dtype=float)
    out=np.eye(4);out[:3,:3]=rot;out[:3,3]=t
    return out


def _motion(kind: str, axis: np.ndarray, value: float) -> np.ndarray:
    if not np.isfinite(value):
        raise ValueError('关节位置不是有效数值')
    result = np.eye(4)
    if kind == 'prismatic':
        result[:3,3] = axis * value
    elif kind in ('revolute','continuous'):
        x,y,z = axis; c,s=math.cos(value), math.sin(value)
        k=1-c
        result[:3,:3]=[[c+x*x*k,x*y*k-z*s,x*z*k+y*s],
                       [y*x*k+z*s,c+y*y*k,y*z*k-x*s],
                       [z*x*k-y*s,z*y*k+x*s,c+z*z*k]]
    elif kind != 'fixed':
        raise ValueError(f'不支持的关节类型 {kind}')
    return result


class RobotModel:
    def __init__(self, xml: str):
        if len(xml.encode('utf-8')) > 5_000_000:
            raise ValueError('URDF 超过允许大小')
        root = ET.fromstring(xml)
        if root.tag != 'robot':
            raise ValueError('文件不是有效的 URDF robot 文档')
        self.name = root.get('name','robot')
        self.links={e.get('name') for e in root.findall('link') if e.get('name')}
        if not self.links:
            raise ValueError('URDF 不包含 Link')
        self.joints={}
        self.adj={name:[] for name in self.links}
        self.child_links=set()
        for e in root.findall('joint'):
            name=e.get('name');kind=e.get('type','')
            parent=e.find('parent');child=e.find('child')
            p=parent.get('link') if parent is not None else None
            q=child.get('link') if child is not None else None
            if not name or name in self.joints or not p or not q or p not in self.links or q not in self.links or p==q:
                raise ValueError('URDF 存在重复或无效的 Joint / Link 关系')
            if kind not in ('fixed','revolute','continuous','prismatic'):
                raise ValueError(f'Joint {name} 类型 {kind} 暂不支持，请使用刚性或普通旋转/移动关节模型')
            if q in self.child_links:
                raise ValueError(f'URDF 中 Link {q} 有多个父关节')
            self.child_links.add(q)
            origin=e.find('origin')
            transform=_matrix_xyz_rpy(origin.get('xyz','0 0 0') if origin is not None else '0 0 0',
                                     origin.get('rpy','0 0 0') if origin is not None else '0 0 0')
            ax=e.find('axis');axis=np.fromstring(ax.get('xyz','1 0 0') if ax is not None else '1 0 0',sep=' ',dtype=float)
            if len(axis)!=3 or not np.isfinite(axis).all() or np.linalg.norm(axis)<1e-12:
                raise ValueError(f'Joint {name} 的 axis 无效')
            axis/=np.linalg.norm(axis)
            mimic=e.find('mimic')
            rule=None
            if mimic is not None:
                rule=(mimic.get('joint'),float(mimic.get('multiplier','1')),float(mimic.get('offset','0')))
            self.joints[name]=dict(name=name,kind=kind,parent=p,child=q,origin=transform,axis=axis,mimic=rule)
            self.adj[p].append((q,name,False))
            self.adj[q].append((p,name,True))
        roots=self.links-self.child_links
        if len(roots)!=1 or len(self.joints)!=len(self.links)-1:
            raise ValueError('URDF 必须描述一棵无环、单根的机器人运动学树')
        self.root=next(iter(roots))
        for link in self.links:
            self._path(self.root,link)

    @classmethod
    def from_file(cls,path: str):
        target=Path(path).expanduser().resolve()
        if not target.is_file() or target.suffix.lower() not in ('.urdf','.xacro'):
            raise ValueError('请选择存在的 .urdf 或 .xacro 文件')
        if target.stat().st_size>5_000_000:
            raise ValueError('机器人模型文件过大')
        if target.suffix.lower()=='.xacro':
            try:
                output=subprocess.run(['xacro',str(target)],capture_output=True,text=True,timeout=12,check=True,cwd=str(target.parent))
            except FileNotFoundError as exc:
                raise ValueError('未安装 xacro，请安装 ROS2 xacro 或先展开为 URDF') from exc
            except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as exc:
                raise ValueError('Xacro 展开失败，请检查模型的依赖文件和宏参数') from exc
            return cls(output.stdout)
        return cls(target.read_text(encoding='utf-8'))

    def _path(self,src: str,dst: str):
        if src not in self.links or dst not in self.links:
            raise ValueError(f'URDF 中不存在 Link：{src if src not in self.links else dst}')
        queue=deque([(src,[])]);seen={src}
        while queue:
            at,path=queue.popleft()
            if at==dst:return path
            for nxt,name,reverse in self.adj[at]:
                if nxt not in seen:
                    seen.add(nxt);queue.append((nxt,path+[(name,reverse)]))
        raise ValueError(f'Link {src} 与 {dst} 不连通')

    def movable_joints(self,src: str,dst: str):
        return [name for name,_ in self._path(src,dst) if self.joints[name]['kind']!='fixed']

    def transform(self,src: str,dst: str,positions: dict[str,float] | None=None,only_fixed=False):
        positions=positions or {}
        result=np.eye(4)
        for name,reverse in self._path(src,dst):
            joint=self.joints[name]
            if joint['kind']!='fixed':
                if only_fixed:
                    raise ValueError(f'从 {src} 到 {dst} 经过活动关节 {name}，仅凭末端位姿和 URDF 无法计算')
                key=name
                if joint['mimic']:
                    key,mult,offset=joint['mimic']
                    if key not in positions:raise ValueError(f'JointState 缺少仿动源关节 {key}')
                    val=positions[key]*mult+offset
                else:
                    if key not in positions:raise ValueError(f'JointState 缺少关节 {key}')
                    val=positions[key]
                step=joint['origin']@_motion(joint['kind'],joint['axis'],val)
            else:step=joint['origin']
            result=result@(np.linalg.inv(step) if reverse else step)
        return result

    def info(self):
        return dict(name=self.name,root=self.root,links=sorted(self.links),joints=len(self.joints),
                    active_joints=[n for n,j in self.joints.items() if j['kind']!='fixed'])


def pose_from_matrix(matrix):
    t=np.asarray(matrix,dtype=float)
    # OpenCV Rodrigues supports matrices near 180 degrees reliably
    # quaternion computed here to keep a single convention x,y,z,w
    m=t[:3,:3];trace=np.trace(m)
    if trace>0:
        s=math.sqrt(max(0.0,trace+1))*2; q=[(m[2,1]-m[1,2])/s,(m[0,2]-m[2,0])/s,(m[1,0]-m[0,1])/s,.25*s]
    else:
        i=int(np.argmax(np.diag(m)))
        if i==0:
            s=2*math.sqrt(max(0,1+m[0,0]-m[1,1]-m[2,2]));q=[.25*s,(m[0,1]+m[1,0])/s,(m[0,2]+m[2,0])/s,(m[2,1]-m[1,2])/s]
        elif i==1:
            s=2*math.sqrt(max(0,1+m[1,1]-m[0,0]-m[2,2]));q=[(m[0,1]+m[1,0])/s,.25*s,(m[1,2]+m[2,1])/s,(m[0,2]-m[2,0])/s]
        else:
            s=2*math.sqrt(max(0,1+m[2,2]-m[0,0]-m[1,1]));q=[(m[0,2]+m[2,0])/s,(m[1,2]+m[2,1])/s,.25*s,(m[1,0]-m[0,1])/s]
    q=np.asarray(q,dtype=float);q/=np.linalg.norm(q)
    return tuple(float(v) for v in (*t[:3,3],*q))
