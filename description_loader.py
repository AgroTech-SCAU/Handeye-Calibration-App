"""Read-only Description snapshot and bounded geometry data for the model inspector

The model is never loaded into a ROS TF publisher or a robot controller
"""
from __future__ import annotations

import math
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from functools import lru_cache

import numpy as np

from robot_model import RobotModel, _matrix_xyz_rpy

SKIP_DIRS = {'.git', '.venv', 'node_modules', '__pycache__', 'build', 'install', 'log', 'dist'}
ALLOW_FILES = {'.urdf', '.xacro', '.stl', '.glb', '.gltf', '.obj', '.dae', '.png', '.jpeg', '.jpg', '.mtl', '.json', '.yaml', '.xml'}
MAX_FILES = 3500
MAX_FILE = 50 * 1024 * 1024
MAX_TOTAL = 180 * 1024 * 1024


def _accepted(parts, extension):
    return not any(p in SKIP_DIRS or p.startswith('.') for p in parts) and extension.lower() in ALLOW_FILES


def _stage_directory(source: Path, dest: Path):
    count = 0
    total = 0
    for path in source.rglob('*'):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(source)
        if not _accepted(rel.parts[:-1], path.suffix):
            continue
        length = path.stat().st_size
        if length > MAX_FILE:
            raise ValueError(f'模型资源文件过大：{rel}')
        count += 1; total += length
        if count > MAX_FILES or total > MAX_TOTAL:
            raise ValueError('Description 资源超过数量或容量限制，请只保留 URDF 与必要 Mesh')
        to = dest / rel
        to.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, to)


def _stage_zip(source: Path, dest: Path):
    if not zipfile.is_zipfile(source):
        raise ValueError('请选择有效的 Description ZIP')
    total = 0; count = 0
    with zipfile.ZipFile(source) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            name = Path(item.filename.replace('\\', '/'))
            if name.is_absolute() or '..' in name.parts or item.filename.startswith('/'):
                raise ValueError('压缩包包含不安全的路径')
            # Symlinks may point out of the extraction directory
            if ((item.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError('Description ZIP 不允许包含符号链接')
            if not _accepted(name.parts[:-1], name.suffix):
                continue
            count += 1; total += item.file_size
            if item.file_size > MAX_FILE or count > MAX_FILES or total > MAX_TOTAL:
                raise ValueError('Description ZIP 超过安全容量限制')
            out = dest / name
            out.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item) as stream, out.open('wb') as target:
                shutil.copyfileobj(stream, target, length=256 * 1024)
    if not count:
        raise ValueError('Description ZIP 内没有可用的模型文件')


def stage_description(source: str, data_dir: Path):
    """Prepare a snapshot without modifying the active one until validation passes"""
    original = Path(source).expanduser().resolve()
    if not original.exists():
        raise ValueError('Description 路径不存在')
    staging = Path(tempfile.mkdtemp(prefix='.handeye-description-', dir=data_dir))
    try:
        if original.is_dir():
            _stage_directory(original, staging)
        elif original.suffix.lower() == '.zip':
            _stage_zip(original, staging)
        elif original.suffix.lower() in ('.urdf', '.xacro'):
            # Standard ROS package layout puts meshes next to the urdf directory
            root = original.parent.parent if original.parent.name.lower() == 'urdf' else original.parent
            _stage_directory(root, staging)
        else:
            raise ValueError('请选择 Description 文件夹、ZIP、URDF 或 Xacro')
        candidates = [p for p in staging.rglob('*') if p.is_file() and p.suffix.lower() in ('.urdf', '.xacro')]
        if not candidates:
            raise ValueError('Description 中找不到 URDF / Xacro')
        def priority(path):
            name = path.name.lower()
            return (int('ros2_control' in name), int('gazebo' in name), int(path.suffix.lower() != '.urdf'), len(path.parts), len(name))
        candidates.sort(key=priority)
        selected = candidates[0]
        if original.is_file() and original.suffix.lower() in ('.urdf', '.xacro'):
            matches = [p for p in candidates if p.name == original.name]
            if matches:
                selected = matches[0]
        model = RobotModel.from_file(str(selected))
        # Keep the original source tree and one expanded URDF for future ROS2/robot_model usage
        if selected.suffix.lower() == '.xacro':
            import subprocess
            expanded = subprocess.run(['xacro', str(selected)], check=True, capture_output=True,
                                      text=True, timeout=20, cwd=str(selected.parent)).stdout
        else:
            expanded = selected.read_text(encoding='utf-8')
        RobotModel(expanded)
        # Expanded file beside the original permits plain relative meshes where possible
        expanded_path = selected.parent / '__handeye_expanded.urdf'
        expanded_path.write_text(expanded, encoding='utf-8')
        rel = expanded_path.relative_to(staging)
        return staging, rel, model
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _vec(text, default):
    if not text:
        return list(default)
    values = [float(v) for v in text.split()]
    if len(values) != len(default) or not all(math.isfinite(v) for v in values):
        raise ValueError('URDF 几何向量不合法')
    return values


# Limit geometry payload while preserving connected surface topology
# Selecting every N-th STL triangle creates holes and should never be used
MAX_PREVIEW_FACES = 10500


def _coherent_preview_faces(triangles, budget=MAX_PREVIEW_FACES):
    """Return a contiguous, vertex-clustered surface instead of scattered faces

    A fast no-extra-dependency replacement for stride-based sampling
    For small models the original surface is retained exactly
    """
    triangles = np.asarray(triangles, dtype=np.float64).reshape(-1, 3, 3)
    good = np.isfinite(triangles).all(axis=(1, 2))
    triangles = triangles[good]
    if len(triangles) <= budget:
        return np.round(triangles.reshape(-1),6).tolist()
    points = triangles.reshape(-1, 3)
    lo = points.min(axis=0)
    span = np.maximum(points.max(axis=0) - lo, 1e-12)
    scale = float(np.max(span))
    # Vertex clustering reduces the number of faces, but never leaves isolated
    # sampled triangles as the previous renderer did
    def cluster(divisions):
        size = max(scale / divisions, 1e-12)
        cells = np.floor((points - lo) / size).astype(np.int64)
        radix = divisions + 4
        keys = (cells[:,0] * radix + cells[:,1]) * radix + cells[:,2]
        _, inverse = np.unique(keys, return_inverse=True)
        faces = inverse.reshape(-1, 3)
        valid = (faces[:,0] != faces[:,1]) & (faces[:,1] != faces[:,2]) & (faces[:,0] != faces[:,2])
        faces = faces[valid]
        if not len(faces):
            return np.zeros((0, 3, 3), dtype=np.float32)
        # Remove duplicate faces introduced by clustering
        _, first = np.unique(np.sort(faces,axis=1),axis=0,return_index=True)
        faces = faces[np.sort(first)]
        groups = int(inverse.max()) + 1
        counts = np.bincount(inverse,minlength=groups)
        centroids = np.column_stack([np.bincount(inverse,weights=points[:,axis],minlength=groups)/counts
                                     for axis in range(3)])
        candidate = centroids[faces].astype(np.float32)
        normals = np.cross(candidate[:,1]-candidate[:,0],candidate[:,2]-candidate[:,0])
        return candidate[np.einsum('ij,ij->i',normals,normals)>(scale*1e-8)**4]
    divisions = 105
    best = None
    for _ in range(4):
        candidate = cluster(divisions)
        if len(candidate) <= budget:
            if best is None or len(candidate)>len(best): best=candidate
            if len(candidate)>budget*.75: break
            divisions=min(250,int(divisions*math.sqrt(budget/max(1,len(candidate)))*.90))
        else:
            divisions=max(8,int(divisions*math.sqrt(budget/len(candidate))*.85))
    return np.round((best if best is not None else cluster(35)).reshape(-1).astype(np.float64),6).tolist()


def _read_stl(path):
    data = path.read_bytes()
    if len(data) >= 84:
        count = int.from_bytes(data[80:84], 'little')
        if 0 < count <= 2000000 and len(data) == 84 + count * 50:
            points = np.ndarray((count,3,3),dtype='<f4',buffer=data,offset=96,strides=(50,12,4))
            return _coherent_preview_faces(points)
    coords = []
    for line in data.decode('utf-8',errors='ignore').splitlines():
        line = line.strip()
        if line.startswith('vertex '):
            try: coords.append([float(x) for x in line.split()[1:4]])
            except ValueError: pass
    if not coords:
        return []
    return _coherent_preview_faces(np.asarray(coords[:len(coords)//3*3]).reshape(-1,3,3))


def _mesh_triangles(path: Path):
    if path.suffix.lower() == '.stl':
        return _read_stl(path), ''
    try:
        import trimesh
        scene = trimesh.load(str(path), force='scene', process=False)
        meshes = [entry for entry in scene.dump() if isinstance(entry,trimesh.Trimesh) and len(entry.faces)]
        faces = [np.asarray(mesh.vertices)[np.asarray(mesh.faces)] for mesh in meshes]
        if not faces:
            return [], ''
        return _coherent_preview_faces(np.concatenate(faces,axis=0)), ''
    except ImportError:
        return [], 'GLB/OBJ 网格预览需要可选依赖 trimesh'
    except Exception as exc:
        return [], f'无法解析网格 {path.name}: {type(exc).__name__}'


def _resolve_mesh(uri: str, urdf_path: Path):
    if not uri or uri.startswith(('http:', 'https:')):
        return None
    base = urdf_path.parent
    root = urdf_path.parents[2] if len(urdf_path.parents) >= 3 and '__handeye_expanded' in urdf_path.name else base
    if uri.startswith('package://'):
        relative = Path(uri[10:])
        paths = [base / relative, base.parent / relative, *[parent / relative for parent in list(base.parents)[:3]]]
        paths += list((root if root.is_dir() else base).rglob(relative.name))[:30]
        for path in paths:
            if path.is_file() and (str(path).endswith(str(relative)) or path.name == relative.name):
                return path.resolve()
        # ROS2 package installed separately, not copied into the local Description snapshot
        try:
            from ament_index_python.packages import get_package_share_directory
            package, suffix = uri[10:].split('/', 1)
            path = Path(get_package_share_directory(package)) / suffix
            if path.is_file():
                return path.resolve()
        except Exception:
            pass
        return None
    if uri.startswith('file://'):
        return Path(uri[7:]).resolve() if Path(uri[7:]).is_file() else None
    path = (base / uri).resolve()
    if path.is_file():
        return path
    for parent in base.parents[:3]:
        candidate = (parent / uri).resolve()
        if candidate.is_file():
            return candidate
    return None


@lru_cache(maxsize=3)
def _static_preview_geometry(urdf_file: Path, file_mtime_ns: int):
    root = ET.fromstring(urdf_file.read_text(encoding='utf-8'))
    links = []
    warnings = []
    mesh_count = 0
    for item in root.findall('link'):
        name = item.get('name')
        visuals = []
        for parent_name in ('visual', 'collision'):
            for element in item.findall(parent_name):
                origin = element.find('origin')
                m = _matrix_xyz_rpy(origin.get('xyz','0 0 0') if origin is not None else '0 0 0',
                                    origin.get('rpy','0 0 0') if origin is not None else '0 0 0')
                geom = element.find('geometry')
                if geom is None:
                    continue
                primitive = None
                verts = []
                for key in ('box','cylinder','sphere','mesh'):
                    child = geom.find(key)
                    if child is None:
                        continue
                    if key == 'box':
                        primitive = {'type':key, 'size':_vec(child.get('size'),[0.1]*3)}
                    elif key == 'cylinder':
                        primitive = {'type':key, 'radius':float(child.get('radius','0.01')),'length':float(child.get('length','0.05'))}
                    elif key == 'sphere':
                        primitive = {'type':key, 'radius':float(child.get('radius','0.01'))}
                    else:
                        uri = child.get('filename','')
                        found = _resolve_mesh(uri, urdf_file)
                        if found and found.stat().st_size <= MAX_FILE:
                            verts, message = _mesh_triangles(found)
                            if message: warnings.append(message)
                            mesh_count += bool(verts)
                        elif uri:
                            warnings.append(f'{name}: 找不到模型网格 {uri}')
                        primitive = {'type':key, 'name':Path(uri).name, 'scale':_vec(child.get('scale'),[1]*3)}
                    break
                if primitive:
                    rgba = None
                    color = element.find('material/color')
                    if color is not None:
                        rgba = _vec(color.get('rgba'), [0.7,0.75,0.82,1.0])
                    visuals.append({'layer': parent_name, 'transform':m.round(8).tolist(),
                                    'geometry':primitive, 'vertices':verts, 'color':rgba})
        links.append({'name':name, 'visuals':visuals})
    return links, tuple(dict.fromkeys(warnings)), mesh_count


def preview_payload(urdf_file: Path, model: RobotModel, positions: dict | None=None):
    links, warnings, mesh_count = _static_preview_geometry(urdf_file, urdf_file.stat().st_mtime_ns)
    positions = positions or {}
    joints = []
    for name,j in model.joints.items():
        joints.append({'name':name,'parent':j['parent'],'child':j['child'],'kind':j['kind'],
                       'axis':j['axis'].tolist(), 'origin':j['origin'].round(9).tolist()})
    frames = {}
    available = True
    try:
        for link in model.links:
            frames[link] = model.transform(model.root,link,positions).round(8).tolist()
    except ValueError:
        available = False
        frames = {link:model.transform(model.root,link,{name:0.0 for name,j in model.joints.items() if j['kind']!='fixed'}).round(8).tolist()
                  for link in model.links}
    return {'name':model.name,'root':model.root,'links':links,'joints':joints,'frames':frames,
            'model_pose':'joint_state' if available and positions else 'illustrative',
            'mesh_count':mesh_count,'warnings':list(dict.fromkeys(warnings))[:18]}
