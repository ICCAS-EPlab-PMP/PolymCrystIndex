#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
visualizer.py — 衍射后处理查看器 FastAPI 后端
提供图像加载、渲染、Miller 点计算等 REST API。
"""

import io
import os
import base64
import math
import tempfile
from copy import copy
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
import numpy as np

from core.config import settings

from services.diffraction_utils import (
    MillerFileParser,
    InfoFileParser,
    ImageRenderer,
    PixelCoordinateCalculator,
    PsiAzimuthMapper,
    draw_raw_markers,
    draw_reference_markers,
)
from services.physics import q_and_psi

try:
    import fabio
    FABIO_OK = True
except Exception:
    FABIO_OK = False

try:
    import pyFAI
    from pyFAI import detector_factory as _detector_factory
    from pyFAI.integrator.azimuthal import AzimuthalIntegrator as _AI_CLS
    PYFAI_OK = True
except Exception:
    PYFAI_OK = False
    _detector_factory = None
    _AI_CLS = None

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager

_FONT_CANDIDATE_PATHS = [
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/msyh.ttf"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
]

_font_names = ['Noto Sans SC', 'SimHei', 'WenQuanYi Micro Hei', 'Microsoft YaHei', 'DejaVu Sans']
for _font_path in _FONT_CANDIDATE_PATHS:
    if _font_path.exists():
        try:
            font_manager.fontManager.addfont(str(_font_path))
            _resolved_name = font_manager.FontProperties(fname=str(_font_path)).get_name()
            _font_names = [_resolved_name] + [name for name in _font_names if name != _resolved_name]
            break
        except Exception:
            continue

plt.rcParams['font.sans-serif'] = _font_names
plt.rcParams['axes.unicode_minus'] = False

router = APIRouter(prefix="/visualizer")


class RawState:
    image: Optional[np.ndarray] = None
    image_shape: tuple = (0, 0)
    ai = None
    calculator: PixelCoordinateCalculator = PixelCoordinateCalculator()
    full_miller: list = []
    output_miller: list = []
    reference_points: list = []


class IntState:
    image: Optional[np.ndarray] = None
    image_shape: tuple = (0, 0)
    q_range: tuple = (0.0, 1.0)
    az_range: tuple = (-180.0, 180.0)
    full_miller: list = []
    output_miller: list = []
    reference_points: list = []
    mapper: PsiAzimuthMapper = PsiAzimuthMapper(convention="ccw", offset=0.0)


raw_state = RawState()
int_state = IntState()


class RawRenderParams(BaseModel):
    contrast_min: float = 0.0
    contrast_max: float = 65535.0
    mode: str = "Linear"
    colormap: str = "灰度"
    show_labels: bool = True
    quadrant: str = "第一象限"
    rot_offset: float = 0.0
    wl: float = 1.0
    px: float = 100.0
    py: float = 100.0
    cx: float = 0.0
    cy: float = 0.0
    dist: float = 1000.0
    use_pyfai: bool = True


class BoxIntegrateParams(BaseModel):
    """方框积分请求：用户在原始图像上画的像素矩形 + 几何参数。

    x0/y0/x1/y1 为图像像素坐标（无需排序，端点会自动归一化为左上/右下）。
    """
    x0: int
    y0: int
    x1: int
    y1: int
    npt: int = 500
    threshold_min: float = 0.0
    threshold_max: float = 65535.0
    wl: float = 1.0
    px: float = 100.0
    py: float = 100.0
    cx: float = 0.0
    cy: float = 0.0
    dist: float = 1000.0
    quadrant: str = "第一象限"
    rot_offset: float = 0.0
    use_pyfai: bool = True


def _mask_empty_bins_box(intensity, count) -> list:
    """把无像素贡献的空 bin 标记为 None（与 /peak/raw/integrate 同语义）。"""
    import numpy as _np
    out = _np.array(intensity, dtype=float).copy()
    if count is not None:
        count_arr = _np.asarray(count)
        if count_arr.shape == out.shape:
            out[count_arr == 0] = _np.nan
    return [None if (v != v) else float(v) for v in out.tolist()]  # NaN→None


class Hdf5SliceReq(BaseModel):
    """加载 HDF5 dataset 的特定 2D 切片。

    extra_axes 形如 [{"axis": 0, "mode": "index", "index": 5},
                     {"axis": 1, "mode": "max"}]
    - axis: 数据集中"非最后两维"的轴索引（最后两维默认为 y, x）。
    - mode: "index"（取该索引的单帧）或 "max"/"sum"/"mean"（沿该轴投影）。
    - index: mode=="index" 时使用的整数索引。
    未在 extra_axes 中列出的额外轴默认取索引 0。
    """
    file_key: str
    dataset_path: str
    extra_axes: List[dict] = []


class IntRenderParams(BaseModel):
    contrast_min: float = 0.0
    contrast_max: float = 65535.0
    colormap: str = "灰度"
    convention: str = "ccw"
    psi_offset: float = 0.0
    az_crop_enabled: bool = False
    az_crop_min: float = -30.0
    az_crop_max: float = 120.0
    mode: str = "Linear"


class UpdateRangesBody(BaseModel):
    q_min: float = 0.0
    q_max: float = 1.0
    az_min: float = -180.0
    az_max: float = 180.0


class WorkDirBody(BaseModel):
    work_dir: str


class MillerOverlayGroup(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    label: str = ""
    content: str = Field(default="", alias="full_miller_content")
    output_content: str = Field(default="", alias="output_miller_content")


class RawSetMillerBody(BaseModel):
    groups: List[MillerOverlayGroup] = []


def _parse_reference_file(content: str) -> list:
    """解析峰提取格式的参考点文件。

    TXT 格式 (tab 分隔):
        q        psi_deg         1
    CSV 格式 (含表头):
        index,pixel_x,pixel_y,intensity,q_A-1,psi_deg_raw,psi_deg_corrected

    返回 [{'h': 0, 'k': 0, 'l': 0, 'q': float, 'psi': float}, ...]
    """
    lines = content.strip().splitlines()
    if not lines:
        return []

    # 判断是否为 CSV (含逗号)
    is_csv = ',' in lines[0]
    result = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if is_csv:
            parts = [p.strip() for p in line.split(',')]
            # 跳过表头行
            if parts[0].startswith('index') or parts[0].startswith('q'):
                continue
            # CSV: index,pixel_x,pixel_y,intensity,q_A-1,psi_deg_raw,psi_deg_corrected
            if len(parts) >= 6:
                psi_col = min(5, len(parts) - 1)  # psi_deg_raw 或 psi_deg_corrected
                q_col = 4
                try:
                    q_val = float(parts[q_col])
                    psi_val = float(parts[psi_col])
                    result.append({'h': 0, 'k': 0, 'l': 0, 'q': q_val, 'psi': psi_val})
                except (ValueError, IndexError):
                    continue
        else:
            # TXT: q  psi  1
            parts = line.split()
            if len(parts) >= 2:
                try:
                    q_val = float(parts[0])
                    psi_val = float(parts[1])
                    result.append({'h': 0, 'k': 0, 'l': 0, 'q': q_val, 'psi': psi_val})
                except (ValueError, IndexError):
                    continue
    return result


def _load_poni_into_raw_state(poni_path: Path) -> Optional[dict]:
    if not PYFAI_OK or not poni_path.exists():
        return None
    ai = pyFAI.load(str(poni_path))
    raw_state.calculator.set_pyfai_geometry_v2(ai)
    return {
        "wl": round(ai.wavelength * 1e10, 6),
        "px": round(ai.detector.pixel2 * 1e6, 4),
        "py": round(ai.detector.pixel1 * 1e6, 4),
        "cx": round(ai.poni2 / ai.detector.pixel2, 2),
        "cy": round(ai.poni1 / ai.detector.pixel1, 2),
        "dist": round(ai.dist * 1e3, 4),
    }


def _find_first_existing(base_dir: Path, patterns: List[str]) -> Optional[Path]:
    for pattern in patterns:
        matches = sorted(base_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def load_image_auto(data: bytes, filename: str) -> np.ndarray:
    """根据扩展名自动选择加载器"""
    name_lower = filename.lower()

    if name_lower.endswith(('.h5', '.hdf5')):
        raise ValueError(
            "HDF5 文件请使用专用流程（probe-hdf5 + load-hdf5-slice），"
            "以便选择 dataset 与切片。"
        )

    if name_lower.endswith('.npy'):
        arr = np.load(io.BytesIO(data))
        if arr.ndim != 2:
            raise ValueError("npy 文件必须是二维数组")
        return arr.astype(np.float64)

    if name_lower.endswith(('.tif', '.tiff')):
        if FABIO_OK:
            with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tf:
                tf.write(data)
                tf_path = tf.name
            try:
                arr = fabio.open(tf_path).data
                return arr.astype(np.float64)
            finally:
                os.unlink(tf_path)
        else:
            from PIL import Image
            img = Image.open(io.BytesIO(data))
            return np.array(img, dtype=np.float64)

    if FABIO_OK:
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tf:
            tf.write(data)
            tf_path = tf.name
        try:
            arr = fabio.open(tf_path).data
            return arr.astype(np.float64)
        finally:
            os.unlink(tf_path)

    raise ValueError(f"不支持的文件格式: {filename}（请安装 fabio）")


# ============ HDF5 支持 ============

H5_OK = False
try:
    import h5py
    H5_OK = True
except Exception:
    H5_OK = False

# file_key → 临时文件路径。探测后的 HDF5 文件保留于此，供 load-hdf5-slice 复用。
_hdf5_cache: dict[str, str] = {}


def _is_hdf5(filename: str) -> bool:
    return filename.lower().endswith(('.h5', '.hdf5'))


def _probe_hdf5_datasets(path: str) -> list[dict]:
    """递归扫描 HDF5 文件中所有 ndim>=2 的 dataset，返回元信息列表。"""
    out = []
    if not H5_OK:
        return out
    with h5py.File(path, 'r') as f:
        def _visit(name, obj):
            if isinstance(obj, h5py.Dataset) and obj.ndim >= 2:
                out.append({
                    "path": "/" + name if not name.startswith("/") else name,
                    "shape": list(obj.shape),
                    "ndim": int(obj.ndim),
                    "dtype": str(obj.dtype),
                    "size": int(obj.size),
                })
        f.visititems(_visit)
    # 优先把"看起来像图像"的大数据集排在前面
    out.sort(key=lambda d: d["size"], reverse=True)
    return out


def image_stats(arr: np.ndarray) -> dict:
    mn = float(np.min(arr))
    mx = float(np.max(arr))
    p99 = float(np.percentile(arr, 99.9)) if arr.size > 1 else mx
    p01 = float(np.percentile(arr, 0.1)) if arr.size > 1 else mn
    # 前 1% 最强像素的中位数:作为方框积分阈值的推荐上限,比单一最亮像素
    # 更稳健(不受热点/坏点主导),能代表"真实强信号"水平。
    top1_median = mx
    if arr.size > 1:
        try:
            cutoff = float(np.percentile(arr, 99))  # 前 1% 的下界
            strong = arr[arr >= cutoff]
            if strong.size > 0:
                top1_median = float(np.median(strong))
        except Exception:
            top1_median = mx
    return {"min": mn, "max": mx, "p01": p01, "p99": p99, "top1pct_median": top1_median}


def mpl_fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


@router.get("/status")
def get_status():
    return {
        "version": "3.1",
        "fabio": FABIO_OK,
        "pyfai": PYFAI_OK,
        "raw_image_loaded": raw_state.image is not None,
        "raw_image_shape": list(raw_state.image_shape) if raw_state.image is not None else None,
        "raw_full_miller": len(raw_state.full_miller),
        "raw_output_miller": len(raw_state.output_miller),
        "raw_reference_points": len(raw_state.reference_points),
        "int_image_loaded": int_state.image is not None,
        "int_image_shape": list(int_state.image_shape) if int_state.image is not None else None,
        "int_full_miller": len(int_state.full_miller),
        "int_output_miller": len(int_state.output_miller),
        "int_reference_points": len(int_state.reference_points),
        "int_q_range": list(int_state.q_range),
        "int_az_range": list(int_state.az_range),
    }


@router.post("/raw/upload-image")
async def raw_upload_image(file: UploadFile = File(...)):
    """上传原始衍射图像 (.tif/.edf/.cbf)"""
    data = await file.read()
    try:
        arr = load_image_auto(data, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"图像加载失败: {e}")

    raw_state.image = arr
    raw_state.image_shape = arr.shape
    raw_state.full_miller = []
    raw_state.output_miller = []
    raw_state.reference_points = []
    raw_state.ai = None
    raw_state.calculator.clear_invert_geom()

    stats = image_stats(arr)
    h, w = arr.shape
    return {
        "message": f"已加载: {file.filename}  ({w}×{h})",
        "width": w, "height": h,
        **stats,
        "pyfai_available": PYFAI_OK,
    }


@router.post("/raw/probe-hdf5")
async def raw_probe_hdf5(file: UploadFile = File(...)):
    """探测 HDF5 文件中的 dataset（ndim>=2），返回供前端选择的列表。

    文件被缓存到临时目录，返回 file_key 供后续 /raw/load-hdf5-slice 使用。
    """
    if not H5_OK:
        raise HTTPException(status_code=400, detail="h5py 未安装，无法读取 HDF5。")
    data = await file.read()
    suffix = os.path.splitext(file.filename)[1] or '.h5'
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
        tf.write(data)
        tf_path = tf.name
    try:
        datasets = _probe_hdf5_datasets(tf_path)
    except Exception as e:
        os.unlink(tf_path)
        raise HTTPException(status_code=400, detail=f"HDF5 解析失败: {e}")
    if not datasets:
        os.unlink(tf_path)
        raise HTTPException(status_code=400, detail="HDF5 中未找到 ndim>=2 的 dataset。")

    # 生成 file_key 并缓存路径（清理旧的缓存项以防膨胀）
    import uuid as _uuid
    file_key = _uuid.uuid4().hex
    _hdf5_cache[file_key] = tf_path
    _gc_hdf5_cache()

    return {
        "file_key": file_key,
        "filename": file.filename,
        "datasets": datasets,
    }


def _gc_hdf5_cache(max_items: int = 8):
    """保留最近 max_items 个 HDF5 缓存文件，删除多余的并清盘。"""
    if len(_hdf5_cache) <= max_items:
        return
    # 简单策略：按键排序后删除最早的若干个
    for key in list(_hdf5_cache.keys())[: len(_hdf5_cache) - max_items]:
        path = _hdf5_cache.pop(key, None)
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


@router.post("/raw/load-hdf5-slice")
def raw_load_hdf5_slice(req: Hdf5SliceReq):
    """根据用户选择加载 HDF5 dataset 的 2D 切片并存入 raw_state。"""
    if not H5_OK:
        raise HTTPException(status_code=400, detail="h5py 未安装。")
    path = _hdf5_cache.get(req.file_key)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=400, detail="HDF5 文件已过期，请重新上传。")

    try:
        with h5py.File(path, 'r') as f:
            if req.dataset_path not in f:
                raise HTTPException(
                    status_code=400,
                    detail=f"dataset 不存在: {req.dataset_path}",
                )
            ds = f[req.dataset_path]
            if ds.ndim < 2:
                raise HTTPException(status_code=400, detail="所选 dataset 不足 2 维。")

            arr = _materialize_2d_slice(ds, req.extra_axes)
    except HTTPException:
        raise
    except Exception as e:
        import traceback as _tb
        _tb.print_exc()
        raise HTTPException(status_code=500, detail=f"HDF5 切片失败: {e}")

    arr = arr.astype(np.float64)
    raw_state.image = arr
    raw_state.image_shape = arr.shape
    raw_state.full_miller = []
    raw_state.output_miller = []
    raw_state.reference_points = []
    raw_state.ai = None
    raw_state.calculator.clear_invert_geom()

    stats = image_stats(arr)
    h, w = arr.shape
    return {
        "message": f"已加载 HDF5 切片: {req.dataset_path}  ({w}×{h})",
        "width": w, "height": h,
        "dataset_path": req.dataset_path,
        **stats,
        "pyfai_available": PYFAI_OK,
    }


def _materialize_2d_slice(dataset, extra_axes_spec: list) -> np.ndarray:
    """把 ndim>=2 的 dataset 折叠成 2D 数组。

    默认把最后两维当作 (y, x)。其余额外维（原轴号 0..ndim-3）按 extra_axes_spec
    处理：
      - mode="index" + index=N → 取该轴第 N 帧
      - mode="max"/"sum"/"mean" → 沿该轴做对应投影
    未指定的额外轴默认取索引 0。

    实现上从最高的额外轴往最低轴处理；每处理掉一个轴，剩余轴在 arr 中的位置
    保持稳定（始终 < 当前 ndim-2），因此轴号不会错位。
    """
    ndim = dataset.ndim
    if ndim < 2:
        raise ValueError("dataset 必须 >=2 维")

    spec_by_axis = {int(s["axis"]): s for s in (extra_axes_spec or [])}

    arr = np.array(dataset[...])  # 读入内存
    # 从最高额外轴（原轴号 ndim-3）往最低（0）处理。
    for axis in range(ndim - 3, -1, -1):
        if arr.ndim <= 2:
            break
        spec = spec_by_axis.get(axis, {})
        mode = spec.get("mode", "index")
        if mode == "index":
            idx = int(spec.get("index", 0))
            size = arr.shape[axis]
            idx = max(0, min(idx, size - 1))
            arr = np.take(arr, idx, axis=axis)
        elif mode == "max":
            arr = np.nanmax(arr, axis=axis)
        elif mode == "sum":
            arr = np.nansum(arr, axis=axis)
        else:  # mean
            arr = np.nanmean(arr, axis=axis)

    if arr.ndim != 2:
        raise ValueError(f"切片后维度异常: ndim={arr.ndim}")
    return arr


@router.post("/raw/upload-poni")
async def raw_upload_poni(file: UploadFile = File(...)):
    """上传 PONI 文件，自动提取仪器参数"""
    if not PYFAI_OK:
        raise HTTPException(status_code=400, detail="pyFAI 未安装，无法加载 PONI 文件")

    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix='.poni', delete=False, mode='wb') as tf:
        tf.write(data)
        tf_path = tf.name
    try:
        ai = pyFAI.load(tf_path)
        
        wl_ang = ai.wavelength * 1e10
        px_um = ai.detector.pixel2 * 1e6
        py_um = ai.detector.pixel1 * 1e6
        dist_mm = ai.dist * 1e3
        cx_px = ai.poni2 / ai.detector.pixel2
        cy_px = ai.poni1 / ai.detector.pixel1

        raw_state.calculator.set_pyfai_geometry_v2(ai)

        return {
            "message": f"PONI 已加载: {file.filename}",
            "wl": round(wl_ang, 6),
            "px": round(px_um, 4),
            "py": round(py_um, 4),
            "cx": round(cx_px, 2),
            "cy": round(cy_px, 2),
            "dist": round(dist_mm, 4),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"PONI 解析失败: {e}")
    finally:
        os.unlink(tf_path)


@router.post("/raw/upload-miller")
async def raw_upload_miller(
    file: UploadFile = File(...),
    miller_type: str = Query("full", description="full | output"),
):
    """上传 Miller 文件"""
    content = (await file.read()).decode('utf-8', errors='replace')
    data = MillerFileParser.parse(content)
    if not data:
        raise HTTPException(status_code=400, detail="无法从文件解析有效 Miller 数据")

    if miller_type == "full":
        raw_state.full_miller = data
    else:
        raw_state.output_miller = data

    label = "FullMiller" if miller_type == "full" else "outputMiller"
    return {"message": f"已导入 {len(data)} 个 {label} 点 ← {file.filename}", "count": len(data)}


@router.post("/raw/set-miller-content")
def raw_set_miller_content(body: RawSetMillerBody):
    """Directly set overlay Miller groups from raw text content for preview."""
    merged_full: List[dict] = []
    merged_output: List[dict] = []
    accepted_groups = body.groups[:5]
    for idx, group in enumerate(accepted_groups):
        parsed_full = MillerFileParser.parse(group.content or "")
        parsed_output = MillerFileParser.parse(group.output_content or "")
        for pt in parsed_full:
            merged_full.append({
                **pt,
                "overlay_index": idx,
                "overlay_label": group.label or f"group_{idx + 1}",
            })
        for pt in parsed_output:
            merged_output.append({
                **pt,
                "overlay_index": idx,
                "overlay_label": group.label or f"group_{idx + 1}",
            })
    raw_state.full_miller = merged_full
    raw_state.output_miller = merged_output
    return {
        "message": f"已装载 {len(accepted_groups)} 组 Miller 叠加数据",
        "group_count": len(accepted_groups),
        "count": len(merged_full) + len(merged_output),
        "total_count": len(merged_full) + len(merged_output),
        "full_miller_count": len(raw_state.full_miller),
        "output_miller_count": len(raw_state.output_miller),
    }


@router.post("/raw/load-workdir")
def raw_load_workdir(body: WorkDirBody):
    """Best-effort load image/PONI/Miller files from a work directory for quick preview."""
    try:
        work_dir = Path(body.work_dir).expanduser().resolve()
    except Exception:
        return {
            "image_loaded": False,
            "width": 0,
            "height": 0,
            "min": 0.0,
            "max": 0.0,
            "p01": 0.0,
            "p99": 0.0,
            "poni": None,
            "full_miller_count": 0,
            "output_miller_count": 0,
            "message": f"工作目录无效: {body.work_dir}",
        }
    if not work_dir.exists() or not work_dir.is_dir():
        return {
            "image_loaded": False,
            "width": 0,
            "height": 0,
            "min": 0.0,
            "max": 0.0,
            "p01": 0.0,
            "p99": 0.0,
            "poni": None,
            "full_miller_count": 0,
            "output_miller_count": 0,
            "message": f"工作目录不存在: {body.work_dir}",
        }

    image_path = _find_first_existing(work_dir, ["*.tif", "*.tiff", "*.edf", "*.cbf", "*.img"])
    poni_path = _find_first_existing(work_dir, ["*.poni"])
    result_dir = work_dir / "result"
    full_miller_path = _find_first_existing(work_dir, ["FullMiller.txt", "result/FullMiller.txt"])
    output_miller_path = _find_first_existing(work_dir, ["outputMiller.txt", "result/outputMiller.txt"])

    result = {
        "image_loaded": False,
        "width": 0,
        "height": 0,
        "min": 0.0,
        "max": 0.0,
        "p01": 0.0,
        "p99": 0.0,
        "poni": None,
        "full_miller_count": 0,
        "output_miller_count": 0,
        "full_miller_content": "",
        "output_miller_content": "",
        "message": "",
    }

    if image_path and image_path.exists():
        try:
            arr = load_image_auto(image_path.read_bytes(), image_path.name)
            raw_state.image = arr
            raw_state.image_shape = arr.shape
            raw_state.ai = None
            raw_state.calculator.clear_invert_geom()
            stats = image_stats(arr)
            h, w = arr.shape
            result.update({
                "image_loaded": True,
                "width": w,
                "height": h,
                **stats,
            })
        except Exception as exc:
            result["message"] = f"加载工作目录图像失败: {exc}"
            return result

    if full_miller_path and full_miller_path.exists():
        full_text = full_miller_path.read_text(encoding='utf-8', errors='replace')
        raw_state.full_miller = MillerFileParser.parse(full_text)
        result["full_miller_count"] = len(raw_state.full_miller)
        result["full_miller_content"] = full_text
    else:
        raw_state.full_miller = []

    if output_miller_path and output_miller_path.exists():
        output_text = output_miller_path.read_text(encoding='utf-8', errors='replace')
        raw_state.output_miller = MillerFileParser.parse(output_text)
        result["output_miller_count"] = len(raw_state.output_miller)
        result["output_miller_content"] = output_text
    else:
        raw_state.output_miller = []

    if poni_path and poni_path.exists():
        try:
            result["poni"] = _load_poni_into_raw_state(poni_path)
        except Exception as exc:
            result["message"] = f"加载工作目录 PONI 失败: {exc}"
            return result

    if not result["message"]:
        result["message"] = f"已检查工作目录: {work_dir.name}"

    return result


@router.delete("/raw/miller")
def raw_clear_miller(
    miller_type: str = Query("all", description="full | output | all"),
):
    if miller_type in ("full", "all"):
        raw_state.full_miller = []
    if miller_type in ("output", "all"):
        raw_state.output_miller = []
    return {"message": "已清除标记点"}


@router.post("/raw/reference-points")
async def raw_upload_reference_points(file: UploadFile = File(...)):
    """上传参考点文件（峰提取格式），从 q+psi 计算像素坐标后存储"""
    if raw_state.image is None:
        raise HTTPException(status_code=400, detail="请先上传图像")

    content = (await file.read()).decode('utf-8', errors='replace')
    data = _parse_reference_file(content)
    if not data:
        raise HTTPException(status_code=400, detail="无法从文件解析有效参考点数据")

    raw_state.reference_points = data
    return {"message": f"已导入 {len(data)} 个参考点 ← {file.filename}", "count": len(data)}


@router.delete("/raw/reference-points")
def raw_clear_reference_points():
    raw_state.reference_points = []
    return {"message": "已清除参考点"}


@router.post("/raw/image-only")
def raw_image_only(params: RawRenderParams):
    """仅返回纯图像（无标记），用于分层渲染优化"""
    if raw_state.image is None:
        raise HTTPException(status_code=400, detail="请先上传图像")

    pil_img = ImageRenderer.to_pil_image(
        raw_state.image,
        params.contrast_min, params.contrast_max,
        params.mode, params.colormap,
    )

    h, w = raw_state.image.shape
    return {
        "image": ImageRenderer.to_png_b64(pil_img),
        "width": w, "height": h,
    }


@router.post("/raw/markers")
def raw_markers(params: RawRenderParams):
    """仅返回Miller标记点坐标，前端用Canvas绘制"""
    if raw_state.image is None:
        raise HTTPException(status_code=400, detail="请先上传图像")

    calc = raw_state.calculator
    calc.set_manual_params(
        wl=params.wl, px=params.px, py=params.py,
        cx=params.cx, cy=params.cy, dist=params.dist,
    )
    calc.set_quadrant(params.quadrant)

    if params.use_pyfai and PYFAI_OK:
        calc.build_invert_geom_from_params()

    h, w = raw_state.image_shape

    def compute_pts(raw_list):
        pts = []
        for pt in raw_list:
            coords = calc.compute(pt['q'], pt['psi'], params.rot_offset)
            if coords is None:
                continue
            x, y = coords
            if 0 <= x < w and 0 <= y < h:
                pts.append({
                    'h': pt['h'], 'k': pt['k'], 'l': pt['l'], 'x': x, 'y': y,
                    'overlay_index': pt.get('overlay_index', 0),
                    'overlay_label': pt.get('overlay_label', ''),
                })
        return pts

    full_pts = compute_pts(raw_state.full_miller)
    output_pts = compute_pts(raw_state.output_miller)

    return {
        "full_miller": full_pts,
        "output_miller": output_pts,
        "cx": params.cx,
        "cy": params.cy,
        "show_labels": params.show_labels,
        "full_miller_count": len(full_pts),
        "output_miller_count": len(output_pts),
        "pyfai_used": calc.has_invert_geom,
    }


def _compute_miller_pixels(calc, miller_list, w, h, rot_offset):
    """共享 helper：对 Miller 列表调用 calc.compute 得到落在图像范围内的像素点。

    返回 [{'h','k','l','q','psi','x','y','overlay_index','overlay_label'}]，
    其中 q/psi 为原始 Å⁻¹/度 值，便于前端展示。
    """
    pts = []
    for pt in miller_list:
        coords = calc.compute(pt['q'], pt['psi'], rot_offset)
        if coords is None:
            continue
        x, y = coords
        if 0 <= x < w and 0 <= y < h:
            pts.append({
                'h': pt['h'], 'k': pt['k'], 'l': pt['l'],
                'q': pt['q'], 'psi': pt['psi'],
                'x': int(round(x)), 'y': int(round(y)),
                'overlay_index': pt.get('overlay_index', 0),
                'overlay_label': pt.get('overlay_label', ''),
            })
    return pts


@router.post("/raw/integrate-box")
def raw_integrate_box(params: BoxIntegrateParams):
    """在用户绘制的像素矩形内做径向积分，并返回落在矩形内的 Miller 点。

    返回:
        q_values, i_q           — q(Å⁻¹) vs 积分强度
        two_theta, d_spacing    — 同一曲线上每个 q 对应的 2θ(°) / d(Å)
        miller_in_box           — 矩形内 Miller 点（hkl + 像素 + q/psi + intensity）
        box                     — 归一化后的矩形 {x0,y0,x1,y1}
    """
    if raw_state.image is None:
        raise HTTPException(status_code=400, detail="请先上传图像")
    if not PYFAI_OK or _AI_CLS is None or _detector_factory is None:
        raise HTTPException(status_code=400, detail="pyFAI not installed.")

    image = raw_state.image
    h, w = raw_state.image_shape

    # 归一化矩形为左上/右下（min/max），并裁剪到图像范围。
    x0 = max(0, min(params.x0, params.x1))
    x1 = min(w - 1, max(params.x0, params.x1))
    y0 = max(0, min(params.y0, params.y1))
    y1 = min(h - 1, max(params.y0, params.y1))
    if x1 <= x0 or y1 <= y0:
        raise HTTPException(status_code=400, detail="矩形无效或完全落在图像外。")

    # 复用 raw_state.calculator 计算 Miller 像素坐标，与 /raw/markers 一致。
    calc = raw_state.calculator
    calc.set_manual_params(
        wl=params.wl, px=params.px, py=params.py,
        cx=params.cx, cy=params.cy, dist=params.dist,
    )
    calc.set_quadrant(params.quadrant)
    if params.use_pyfai and PYFAI_OK:
        calc.build_invert_geom_from_params()

    try:
        # —— pyFAI 积分器构造（照搬 peak_raw.integrate） ——
        wl_m = params.wl * 1e-10
        px_m = params.px * 1e-6
        py_m = params.py * 1e-6
        det = _detector_factory('detector', config={'pixel1': py_m, 'pixel2': px_m})
        ai = _AI_CLS(detector=det, wavelength=wl_m)
        ai.dist = params.dist * 1e-3
        ai.poni1 = params.cy * py_m
        ai.poni2 = params.cx * px_m
        ai.rot1 = 0.0
        ai.rot2 = 0.0
        ai.rot3 = 0.0

        # 组合掩膜：threshold 外的像素 + 矩形外的像素，全部置 1（mask=1 表示忽略）。
        thresh_mask = np.where(
            (image >= params.threshold_min) & (image <= params.threshold_max), 0, 1
        ).astype(np.int8)
        rect_mask = np.ones((h, w), dtype=np.int8)
        rect_mask[y0:y1 + 1, x0:x1 + 1] = 0
        combined_mask = np.where((thresh_mask == 1) | (rect_mask == 1), 1, 0).astype(np.int8)

        npt = max(2, min(int(params.npt), 5000))
        res_q = ai.integrate1d_ng(
            image,
            npt,
            unit="q_A^-1",
            method="splitpixel",
            correctSolidAngle=False,
            mask=combined_mask,
        )
        q_axis = np.array(res_q.radial, dtype=float)
        count = getattr(res_q, "count", None)
        i_q = _mask_empty_bins_box(res_q.intensity, count)

        # q → 2θ / d 本地换算（避免再跑两次 integrate1d，保证三点严格对齐）。
        wl_a = params.wl  # Å
        two_theta = []
        d_spacing = []
        for q in q_axis.tolist():
            if q is None or q <= 0:
                two_theta.append(None)
                d_spacing.append(None)
                continue
            sin_theta = q * wl_a / (4.0 * math.pi)
            if abs(sin_theta) >= 1.0:
                two_theta.append(None)
                d_spacing.append(None)
                continue
            tt = 2.0 * math.degrees(math.asin(sin_theta))
            two_theta.append(tt)
            d_spacing.append((2.0 * math.pi) / q)

        # —— 矩形内 Miller 点筛选 ——
        full_pts = _compute_miller_pixels(
            calc, raw_state.full_miller, w, h, params.rot_offset
        )
        output_pts = _compute_miller_pixels(
            calc, raw_state.output_miller, w, h, params.rot_offset
        )

        def _in_box_and_enrich(pt):
            px_, py_ = pt['x'], pt['y']
            if not (x0 <= px_ <= x1 and y0 <= py_ <= y1):
                return None
            in_thresh = (
                params.threshold_min <= image[py_, px_]
                <= params.threshold_max
            )
            pt = dict(pt)
            pt['intensity'] = float(image[py_, px_]) if in_thresh else None
            # 附 2θ / d
            q_val = pt.get('q')
            if q_val and q_val > 0:
                sin_theta = q_val * wl_a / (4.0 * math.pi)
                if abs(sin_theta) < 1.0:
                    pt['two_theta'] = 2.0 * math.degrees(math.asin(sin_theta))
                    pt['d_spacing'] = (2.0 * math.pi) / q_val
                else:
                    pt['two_theta'] = None
                    pt['d_spacing'] = None
            else:
                pt['two_theta'] = None
                pt['d_spacing'] = None
            return pt

        miller_in_box = []
        for pt in full_pts + output_pts:
            enriched = _in_box_and_enrich(pt)
            if enriched is not None:
                miller_in_box.append(enriched)

        # —— 方框覆盖范围（把 4 个角点的像素坐标转成 q，再算 2θ/d 的 min/max） ——
        # 用于前端在"显示单位=q/2θ/d"时报告方框覆盖的散射范围。
        corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
        corner_qs = []
        for cxp, cyp in corners:
            try:
                cq, _ = q_and_psi(
                    cxp, cyp,
                    params.wl, params.px, params.py,
                    params.cx, params.cy, params.dist,
                )
                corner_qs.append(cq)
            except Exception:
                continue
        if corner_qs:
            q_min_box, q_max_box = float(min(corner_qs)), float(max(corner_qs))
            two_theta_min_box = d_max_box = None
            two_theta_max_box = d_min_box = None
            for cq in corner_qs:
                if cq <= 0:
                    continue
                sin_th = cq * wl_a / (4.0 * math.pi)
                if abs(sin_th) >= 1.0:
                    continue
                tt = 2.0 * math.degrees(math.asin(sin_th))
                dd = (2.0 * math.pi) / cq
                two_theta_min_box = tt if two_theta_min_box is None else min(two_theta_min_box, tt)
                two_theta_max_box = tt if two_theta_max_box is None else max(two_theta_max_box, tt)
                d_max_box = dd if d_max_box is None else max(d_max_box, dd)
                d_min_box = dd if d_min_box is None else min(d_min_box, dd)
            box_coverage = {
                "q": [q_min_box, q_max_box],
                "two_theta": [two_theta_min_box, two_theta_max_box],
                "d_spacing": [d_min_box, d_max_box],
            }
        else:
            box_coverage = {"q": None, "two_theta": None, "d_spacing": None}

        return {
            "q_values": [float(v) for v in q_axis.tolist()],
            "i_q": i_q,
            "two_theta": two_theta,
            "d_spacing": d_spacing,
            "miller_in_box": miller_in_box,
            "miller_in_box_count": len(miller_in_box),
            "box": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
            "box_coverage": box_coverage,
            "image_shape": {"w": int(w), "h": int(h)},
            "pyfai_used": calc.has_invert_geom,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback as _tb
        _tb.print_exc()
        raise HTTPException(status_code=500, detail=f"方框积分失败: {e}")


@router.post("/raw/render")
def raw_render(params: RawRenderParams):
    """渲染原始衍射图（含 Miller 标记），返回 base64 PNG"""
    if raw_state.image is None:
        raise HTTPException(status_code=400, detail="请先上传图像")

    calc = raw_state.calculator
    calc.set_manual_params(
        wl=params.wl, px=params.px, py=params.py,
        cx=params.cx, cy=params.cy, dist=params.dist,
    )
    calc.set_quadrant(params.quadrant)

    if params.use_pyfai and PYFAI_OK:
        calc.build_invert_geom_from_params()

    pil_img = ImageRenderer.to_pil_image(
        raw_state.image,
        params.contrast_min, params.contrast_max,
        params.mode, params.colormap,
    )

    h, w = raw_state.image_shape

    def compute_pts(raw_list):
        pts = []
        for pt in raw_list:
            coords = calc.compute(pt['q'], pt['psi'], params.rot_offset)
            if coords is None:
                continue
            x, y = coords
            if 0 <= x < w and 0 <= y < h:
                pts.append({
                    'h': pt['h'], 'k': pt['k'], 'l': pt['l'], 'x': x, 'y': y,
                    'overlay_index': pt.get('overlay_index', 0),
                    'overlay_label': pt.get('overlay_label', ''),
                })
        return pts

    full_pts = compute_pts(raw_state.full_miller)
    output_pts = compute_pts(raw_state.output_miller)

    ref_pts = compute_pts(raw_state.reference_points)

    pil_marked = draw_raw_markers(
        pil_img, full_pts, output_pts,
        params.cx, params.cy,
        show_labels=params.show_labels,
        ref_pts=ref_pts,
    )
    return {
        "image": ImageRenderer.to_png_b64(pil_marked),
        "width": w, "height": h,
        "full_miller_count": len(full_pts),
        "output_miller_count": len(output_pts),
        "reference_points_count": len(ref_pts),
        "pyfai_used": calc.has_invert_geom,
    }


@router.post("/int/upload-image")
async def int_upload_image(file: UploadFile = File(...)):
    """上传 2D 积分图像 (.npy/.tif)"""
    data = await file.read()
    try:
        arr = load_image_auto(data, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"图像加载失败: {e}")

    if arr.ndim != 2:
        raise HTTPException(status_code=400, detail="图像必须为二维数组")

    int_state.image = arr
    int_state.image_shape = arr.shape
    int_state.full_miller = []
    int_state.output_miller = []
    int_state.reference_points = []

    stats = image_stats(arr)
    h, w = arr.shape
    return {
        "message": f"已加载: {file.filename}  ({w}×{h})",
        "width": w, "height": h,
        **stats,
    }


@router.post("/int/upload-info")
async def int_upload_info(file: UploadFile = File(...)):
    """上传 processing_info.txt，提取坐标范围"""
    content = (await file.read()).decode('utf-8', errors='replace')
    ranges = InfoFileParser.parse(content)
    if not ranges:
        raise HTTPException(status_code=400, detail="无法从文件解析坐标范围")

    if 'q_min' in ranges and 'q_max' in ranges:
        int_state.q_range = (ranges['q_min'], ranges['q_max'])
    if 'az_min' in ranges and 'az_max' in ranges:
        int_state.az_range = (ranges['az_min'], ranges['az_max'])

    return {
        "message": f"坐标范围已从 {file.filename} 加载",
        "q_min": int_state.q_range[0],
        "q_max": int_state.q_range[1],
        "az_min": int_state.az_range[0],
        "az_max": int_state.az_range[1],
    }


@router.post("/int/upload-miller")
async def int_upload_miller(
    file: UploadFile = File(...),
    miller_type: str = Query("full", description="full | output"),
):
    """上传 Miller 文件（2D 积分图用）"""
    content = (await file.read()).decode('utf-8', errors='replace')
    data = MillerFileParser.parse(content)
    if not data:
        raise HTTPException(status_code=400, detail="无法从文件解析有效 Miller 数据")

    if miller_type == "full":
        int_state.full_miller = data
    else:
        int_state.output_miller = data

    label = "FullMiller" if miller_type == "full" else "outputMiller"
    return {"message": f"已导入 {len(data)} 个 {label} 点 ← {file.filename}", "count": len(data)}


@router.post("/int/set-miller-content")
def int_set_miller_content(body: RawSetMillerBody):
    """Directly set overlay Miller groups from raw text content for integrated preview."""
    merged_full: List[dict] = []
    merged_output: List[dict] = []
    accepted_groups = body.groups[:5]
    for idx, group in enumerate(accepted_groups):
        parsed_full = MillerFileParser.parse(group.content or "")
        parsed_output = MillerFileParser.parse(group.output_content or "")
        for pt in parsed_full:
            merged_full.append({
                **pt,
                "overlay_index": idx,
                "overlay_label": group.label or f"group_{idx + 1}",
            })
        for pt in parsed_output:
            merged_output.append({
                **pt,
                "overlay_index": idx,
                "overlay_label": group.label or f"group_{idx + 1}",
            })
    int_state.full_miller = merged_full
    int_state.output_miller = merged_output
    return {
        "message": f"已装载 {len(accepted_groups)} 组 Miller 到 2D 积分图",
        "group_count": len(accepted_groups),
        "count": len(merged_full) + len(merged_output),
        "total_count": len(merged_full) + len(merged_output),
        "full_miller_count": len(int_state.full_miller),
        "output_miller_count": len(int_state.output_miller),
    }


@router.delete("/int/miller")
def int_clear_miller(miller_type: str = Query("all")):
    if miller_type in ("full", "all"):
        int_state.full_miller = []
    if miller_type in ("output", "all"):
        int_state.output_miller = []
    return {"message": "已清除标记点"}


@router.put("/int/coordinate-ranges")
def int_update_ranges(body: UpdateRangesBody):
    """更新 q / azimuth 坐标范围"""
    if body.q_min >= body.q_max:
        raise HTTPException(status_code=400, detail="q_min 必须小于 q_max")
    if body.az_min >= body.az_max:
        raise HTTPException(status_code=400, detail="az_min 必须小于 az_max")
    int_state.q_range = (body.q_min, body.q_max)
    int_state.az_range = (body.az_min, body.az_max)
    return {"message": "坐标范围已更新", "q_range": list(int_state.q_range), "az_range": list(int_state.az_range)}


@router.post("/int/reference-points")
async def int_upload_reference_points(file: UploadFile = File(...)):
    """上传参考点文件（峰提取格式），存储到 2D 积分状态"""
    if int_state.image is None:
        raise HTTPException(status_code=400, detail="请先上传图像")

    content = (await file.read()).decode('utf-8', errors='replace')
    data = _parse_reference_file(content)
    if not data:
        raise HTTPException(status_code=400, detail="无法从文件解析有效参考点数据")

    int_state.reference_points = data
    return {"message": f"已导入 {len(data)} 个参考点 ← {file.filename}", "count": len(data)}


@router.delete("/int/reference-points")
def int_clear_reference_points():
    int_state.reference_points = []
    return {"message": "已清除参考点"}


@router.post("/int/render")
def int_render(params: IntRenderParams):
    """渲染 2D 积分图（含 Miller 标记），返回 base64 PNG"""
    if int_state.image is None:
        raise HTTPException(status_code=400, detail="请先上传图像")

    int_state.mapper.convention = params.convention
    int_state.mapper.offset = params.psi_offset
    mapper = int_state.mapper

    full_mapped = mapper.map_miller_list(int_state.full_miller)
    output_mapped = mapper.map_miller_list(int_state.output_miller)
    ref_mapped = mapper.map_miller_list(int_state.reference_points)

    q_lo, q_hi = int_state.q_range
    az_range = int_state.az_range
    render_image = int_state.image
    crop_start = crop_end = None
    crop_extent = None   # if set, overrides az_range in extent
    if params.az_crop_enabled:
        crop_start, crop_end = mapper.crop_bounds(params.az_crop_min, params.az_crop_max)
        az_values = np.linspace(az_range[0], az_range[1], int_state.image.shape[0])
        mask = np.array(
            [mapper.azimuth_in_crop(az, crop_start, crop_end) for az in az_values],
            dtype=bool,
        )
        indices = np.where(mask)[0]
        if len(indices) > 0:
            if crop_start <= crop_end:
                # non-wrap: contiguous slice
                render_image = int_state.image[indices[0]:indices[-1] + 1]
            else:
                # wrap: two segments — concatenate [az >= start] + [az <= end]
                split = np.where(np.diff(indices) > 1)[0]
                if len(split) > 0:
                    at = split[0] + 1
                    seg_hi = indices[at:]     # az >= start
                    seg_lo = indices[:at]     # az <= end
                    render_image = np.vstack([int_state.image[seg_hi], int_state.image[seg_lo]])
                else:
                    render_image = int_state.image[indices]
            crop_extent = [crop_start, crop_end]
        else:
            # All rows cropped out — use 1-row empty image to avoid matplotlib error
            render_image = int_state.image[:1] * 0
            crop_extent = [crop_start, crop_end]

        def in_crop(azimuth: float) -> bool:
            return mapper.azimuth_in_crop(azimuth, crop_start, crop_end)
    else:
        def in_crop(azimuth: float) -> bool:
            return True

    full_mapped = [
        m for m in full_mapped
        if q_lo <= m['q'] <= q_hi and in_crop(m['az'])
    ]
    output_mapped = [
        m for m in output_mapped
        if q_lo <= m['q'] <= q_hi and in_crop(m['az'])
    ]
    ref_mapped = [
        m for m in ref_mapped
        if q_lo <= m['q'] <= q_hi and in_crop(m['az'])
    ]

    cmap_str = ImageRenderer.mpl_cmap(params.colormap)
    q_range = int_state.q_range
    cmap = copy(plt.get_cmap(cmap_str))

    fig, ax = plt.subplots(figsize=(9, 7))
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#1a1a2e')
    ax.spines['bottom'].set_color('#7ad6fb')
    ax.spines['top'].set_color('#7ad6fb')
    ax.spines['left'].set_color('#7ad6fb')
    ax.spines['right'].set_color('#7ad6fb')
    ax.tick_params(colors='#7096D1', labelsize=10)
    ax.xaxis.label.set_color('#d8eeff')
    ax.yaxis.label.set_color('#d8eeff')
    ax.title.set_color('#d8eeff')

    ax.imshow(
        render_image,
        aspect='auto',
        origin='lower',
        cmap=cmap,
        vmin=params.contrast_min,
        vmax=params.contrast_max,
        extent=[q_range[0], q_range[1], *(crop_extent or [az_range[0], az_range[1]])],
    )
    ax.set_xlabel(r"$q$ ($\AA^{-1}$)", fontsize=12)
    ax.set_ylabel("Azimuth (°)", fontsize=12)
    ax.set_title("2D 积分图像", fontsize=13, color='#d8eeff')

    _MPL_FULL = '#00d2e6'
    _MPL_OUTPUT = '#ff8c00'

    if full_mapped:
        qs = [m['q'] for m in full_mapped]
        azs = [m['az'] for m in full_mapped]
        ax.scatter(qs, azs, s=120, facecolors='none',
                   edgecolors=_MPL_FULL, linewidths=3.5, zorder=10, label="FullMiller")

    if output_mapped:
        qs = [m['q'] for m in output_mapped]
        azs = [m['az'] for m in output_mapped]
        ax.scatter(qs, azs, s=140, marker='D', facecolors='none',
                   edgecolors=_MPL_OUTPUT, linewidths=3.5, zorder=10, label="outputMiller")

    _MPL_REF = '#ffd700'

    if ref_mapped:
        qs = [m['q'] for m in ref_mapped]
        azs = [m['az'] for m in ref_mapped]
        ax.scatter(qs, azs, s=160, marker='*', color=_MPL_REF,
                   linewidths=2, zorder=12, label="Reference Points")

    handles = []
    if full_mapped:
        handles.append(mpatches.Patch(
            facecolor='none', edgecolor=_MPL_FULL, linewidth=3.5, label="FullMiller"))
    if output_mapped:
        handles.append(mpatches.Patch(
            facecolor='none', edgecolor=_MPL_OUTPUT, linewidth=3.5, label="outputMiller"))
    if ref_mapped:
        handles.append(mpatches.Patch(
            facecolor=_MPL_REF, edgecolor=_MPL_REF, linewidth=2, label="Reference Points"))
    if handles:
        ax.legend(handles=handles, loc='upper right', fontsize=10, framealpha=0.9,
                  facecolor='#1a1a2e', edgecolor='#7ad6fb', labelcolor='#d8eeff')

    ax.set_xlim(q_range)
    if crop_extent is not None and crop_start is not None:
        ax.set_ylim(crop_start, crop_end)
    else:
        ax.set_ylim(az_range)

    ax.grid(False)

    fig.tight_layout()
    b64 = mpl_fig_to_b64(fig)
    plt.close(fig)

    return {
        "image": b64,
        "full_miller_count": len(full_mapped),
        "output_miller_count": len(output_mapped),
        "reference_points_count": len(ref_mapped),
    }
