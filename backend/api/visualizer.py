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
)

try:
    import fabio
    FABIO_OK = True
except Exception:
    FABIO_OK = False

try:
    import pyFAI
    PYFAI_OK = True
except Exception:
    PYFAI_OK = False

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


class IntState:
    image: Optional[np.ndarray] = None
    image_shape: tuple = (0, 0)
    q_range: tuple = (0.0, 1.0)
    az_range: tuple = (-180.0, 180.0)
    full_miller: list = []
    output_miller: list = []
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


class RawSetMillerBody(BaseModel):
    groups: List[MillerOverlayGroup] = []


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


def image_stats(arr: np.ndarray) -> dict:
    mn = float(np.min(arr))
    mx = float(np.max(arr))
    p99 = float(np.percentile(arr, 99.9)) if arr.size > 1 else mx
    p01 = float(np.percentile(arr, 0.1)) if arr.size > 1 else mn
    return {"min": mn, "max": mx, "p01": p01, "p99": p99}


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
        "int_image_loaded": int_state.image is not None,
        "int_image_shape": list(int_state.image_shape) if int_state.image is not None else None,
        "int_full_miller": len(int_state.full_miller),
        "int_output_miller": len(int_state.output_miller),
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
    """Directly set up to 5 FullMiller groups from raw text content for overlay preview."""
    merged: List[dict] = []
    accepted_groups = body.groups[:5]
    for idx, group in enumerate(accepted_groups):
        parsed = MillerFileParser.parse(group.content or "")
        for pt in parsed:
            merged.append({
                **pt,
                "overlay_index": idx,
                "overlay_label": group.label or f"group_{idx + 1}",
            })
    raw_state.full_miller = merged
    return {
        "message": f"已装载 {len(accepted_groups)} 组 FullMiller 叠加数据",
        "group_count": len(accepted_groups),
        "count": len(merged),
        "total_count": len(merged),
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
    full_miller_path = work_dir / "FullMiller.txt"
    output_miller_path = work_dir / "outputMiller.txt"

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

    if full_miller_path.exists():
        raw_state.full_miller = MillerFileParser.parse(full_miller_path.read_text(encoding='utf-8', errors='replace'))
        result["full_miller_count"] = len(raw_state.full_miller)
    else:
        raw_state.full_miller = []

    if output_miller_path.exists():
        raw_state.output_miller = MillerFileParser.parse(output_miller_path.read_text(encoding='utf-8', errors='replace'))
        result["output_miller_count"] = len(raw_state.output_miller)
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

    pil_marked = draw_raw_markers(
        pil_img, full_pts, output_pts,
        params.cx, params.cy,
        show_labels=params.show_labels,
    )
    return {
        "image": ImageRenderer.to_png_b64(pil_marked),
        "width": w, "height": h,
        "full_miller_count": len(full_pts),
        "output_miller_count": len(output_pts),
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
    """Directly set up to 5 FullMiller groups from raw text content for integrated overlay preview."""
    merged: List[dict] = []
    accepted_groups = body.groups[:5]
    for idx, group in enumerate(accepted_groups):
        parsed = MillerFileParser.parse(group.content or "")
        for pt in parsed:
            merged.append({
                **pt,
                "overlay_index": idx,
                "overlay_label": group.label or f"group_{idx + 1}",
            })
    int_state.full_miller = merged
    return {
        "message": f"已装载 {len(accepted_groups)} 组 FullMiller 到 2D 积分图",
        "group_count": len(accepted_groups),
        "count": len(merged),
        "total_count": len(merged),
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

    q_lo, q_hi = int_state.q_range
    crop_start = crop_end = None
    crop_mask = None
    az_range = int_state.az_range
    if params.az_crop_enabled:
        crop_start, crop_end = mapper.crop_bounds(params.az_crop_min, params.az_crop_max)
        az_values = np.linspace(az_range[0], az_range[1], int_state.image.shape[0])
        crop_mask = np.array(
            [mapper.azimuth_in_crop(az, crop_start, crop_end) for az in az_values],
            dtype=bool,
        )
    crop_active = crop_start is not None and crop_end is not None
    if crop_active:
        assert crop_start is not None and crop_end is not None

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

    cmap_str = ImageRenderer.mpl_cmap(params.colormap)
    q_range = int_state.q_range
    render_image = int_state.image
    cmap = copy(plt.get_cmap(cmap_str))
    if crop_mask is not None:
        masked_rows = ~crop_mask
        if np.any(masked_rows):
            render_image = np.ma.array(
                int_state.image,
                mask=np.broadcast_to(masked_rows[:, np.newaxis], int_state.image.shape),
            )
            cmap.set_bad(color='#1a1a2e')

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
        extent=[q_range[0], q_range[1], az_range[0], az_range[1]],
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

    handles = []
    if full_mapped:
        handles.append(mpatches.Patch(
            facecolor='none', edgecolor=_MPL_FULL, linewidth=3.5, label="FullMiller"))
    if output_mapped:
        handles.append(mpatches.Patch(
            facecolor='none', edgecolor=_MPL_OUTPUT, linewidth=3.5, label="outputMiller"))
    if handles:
        ax.legend(handles=handles, loc='upper right', fontsize=10, framealpha=0.9,
                  facecolor='#1a1a2e', edgecolor='#7ad6fb', labelcolor='#d8eeff')

    ax.set_xlim(q_range)
    ax.set_ylim(az_range)

    ax.grid(True, color='#2a2a4e', linewidth=0.5)

    fig.tight_layout()
    b64 = mpl_fig_to_b64(fig)
    plt.close(fig)

    return {
        "image": b64,
        "full_miller_count": len(full_mapped),
        "output_miller_count": len(output_mapped),
    }
