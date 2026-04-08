#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diffraction_utils_server.py — 后处理查看器工具库（服务端版，无 Qt 依赖）
将核心功能封装为独立 class，供 FastAPI 后端调用。

模块说明:
  AngleUtils              — 角度归一化
  MillerFileParser        — 解析 FullMiller / outputMiller 文件
  InfoFileParser          — 解析 processing_info.txt (q/azimuth 范围)
  ImageRenderer           — 将原始数组渲染为 PIL Image（线性/Log + 四种色表）
  PixelCoordinateCalculator — (q, ψ) → 像素坐标（pyFAI 或手动几何）
  PsiAzimuthMapper        — ψ → 图像方位角（2D 积分图用）
"""

from __future__ import annotations
from typing import Optional
from pathlib import Path
import math, re, io
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── pyFAI 可选 ──────────────────────────────────────────────────────────────
try:
    import pyFAI
    import pyFAI.units
    from pyFAI.ext.invert_geometry import InvertGeometry
    from pyFAI.integrator.azimuthal import AzimuthalIntegrator
    PYFAI_OK = True
except (ImportError, AttributeError):
    PYFAI_OK = False
    AzimuthalIntegrator = None


_FONT_CANDIDATE_PATHS = [
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/msyh.ttf"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
]


def _ui_font(size: int):
    for font_path in _FONT_CANDIDATE_PATHS:
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


# ═══════════════════════════════════════════════════════════════════════════
# 角度工具
# ═══════════════════════════════════════════════════════════════════════════

class AngleUtils:
    """静态角度工具集"""

    @staticmethod
    def normalize_to_180(angle: float) -> float:
        """将任意角度归一化到 (-180, 180] 区间"""
        angle = (angle % 360 + 360) % 360
        if angle >= 180:
            angle -= 360
        return angle


# ═══════════════════════════════════════════════════════════════════════════
# Miller 文件解析
# ═══════════════════════════════════════════════════════════════════════════

class MillerFileParser:
    """
    通用 Miller 文件解析器。
    自动识别:
      · FullMiller.txt  — 第一行即数据（无列头）, 顺序 H K L q ψ
      · outputMiller.txt — 第一行为列头 "H K L q psi"，后跟数据行
    返回 list of dict: {h, k, l, q, psi}
    """

    @staticmethod
    def parse(content: str) -> list[dict]:
        result = []
        try:
            lines = [ln for ln in content.splitlines() if ln.strip()]
            if not lines:
                return result

            first_tokens = lines[0].strip().split()
            try:
                float(first_tokens[0])
                is_positional = True
            except (ValueError, IndexError):
                is_positional = False

            if is_positional:
                h_idx, k_idx, l_idx, q_idx, psi_idx = 0, 1, 2, 3, 4
                data_lines = lines
            else:
                header_parts = [
                    p.lower()
                    for p in re.split(r'[\s,;|]+', lines[0].strip()) if p.strip()
                ]
                q_idx = psi_idx = h_idx = k_idx = l_idx = -1
                for i, col in enumerate(header_parts):
                    c = col.strip('()')
                    if (c in ('q', 'q_value', 'q_a^-1', 'q_nm')
                            or (col.startswith('q(') and 'theta' not in col)):
                        if q_idx == -1:
                            q_idx = i
                    elif (c in ('psi', 'psi_deg', 'azimuth', 'chi', 'phi')
                          or col.startswith('psi(')
                          or c in ('chi(deg', 'psi(deg')) \
                            and 'root' not in col:
                        if psi_idx == -1:
                            psi_idx = i
                    elif c == 'h':
                        h_idx = i
                    elif c == 'k':
                        k_idx = i
                    elif c in ('l', 'l_'):
                        l_idx = i
                if h_idx == -1 and q_idx == -1:
                    h_idx, k_idx, l_idx, q_idx, psi_idx = 0, 1, 2, 3, 4
                data_lines = lines[1:]

            for line in data_lines:
                parts = line.strip().split()
                if not parts:
                    continue
                try:
                    max_need = max(
                        q_idx, psi_idx,
                        h_idx  if h_idx  >= 0 else 0,
                        k_idx  if k_idx  >= 0 else 0,
                        l_idx  if l_idx  >= 0 else 0,
                    )
                    if len(parts) <= max_need:
                        continue
                    h   = int(float(parts[h_idx]))  if h_idx  >= 0 else 0
                    k   = int(float(parts[k_idx]))  if k_idx  >= 0 else 0
                    l_  = int(float(parts[l_idx]))  if l_idx  >= 0 else 0
                    q   = float(parts[q_idx])
                    psi = float(parts[psi_idx])
                    if math.isnan(q) or math.isnan(psi) or q <= 0:
                        continue
                    result.append({'h': h, 'k': k, 'l': l_, 'q': q, 'psi': psi})
                except (ValueError, IndexError):
                    pass
        except Exception as e:
            print(f"[MillerFileParser] parse error: {e}")
        return result

    @staticmethod
    def parse_file(file_path: str) -> list[dict]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return MillerFileParser.parse(f.read())
        except Exception as e:
            print(f"[MillerFileParser] file read error: {e}")
            return []


# ═══════════════════════════════════════════════════════════════════════════
# 坐标信息文件解析
# ═══════════════════════════════════════════════════════════════════════════

class InfoFileParser:
    """解析 processing_info.txt，提取 q / azimuth 坐标范围"""

    @staticmethod
    def parse(content: str) -> Optional[dict]:
        """返回 {'q_min', 'q_max', 'azimuth_min', 'azimuth_max'}"""
        ranges: dict = {}
        try:
            for line in content.splitlines():
                line = line.strip()
                if "X-axis (q" in line and "range:" in line:
                    parts = line.split("range:")[1].strip().split(" to ")
                    if len(parts) == 2:
                        ranges['q_min'] = float(parts[0])
                        ranges['q_max'] = float(parts[1])
                elif "Y-axis (chi)" in line and "range (degrees):" in line:
                    parts = line.split("range (degrees):")[1].strip().split(" to ")
                    if len(parts) == 2:
                        ranges['azimuth_min'] = float(parts[0])
                        ranges['azimuth_max'] = float(parts[1])
        except Exception as e:
            print(f"[InfoFileParser] parse error: {e}")
            return None
        # normalize key names for consistency
        if 'azimuth_min' in ranges:
            ranges['az_min'] = ranges.pop('azimuth_min')
        if 'azimuth_max' in ranges:
            ranges['az_max'] = ranges.pop('azimuth_max')
        return ranges if ranges else None


# ═══════════════════════════════════════════════════════════════════════════
# 图像渲染（PIL 版，替换原 ColormapRenderer）
# ═══════════════════════════════════════════════════════════════════════════

class ImageRenderer:
    """
    将原始二维 numpy 数组渲染为 PIL.Image。
    支持线性 / Log 两种动态范围，以及四种色表。
    """

    MPL_NAME: dict[str, str] = {
        "灰度": "gray", "反转灰度": "gray_r", "热力图": "hot", "彩虹": "jet"
    }

    @staticmethod
    def normalize(
        img_data: np.ndarray,
        contrast_min: float,
        contrast_max: float,
        mode: str = "Linear",
    ) -> np.ndarray:
        """归一化到 [0,1]"""
        norm = np.clip(img_data.astype(np.float64), contrast_min, contrast_max)
        if mode == "Log":
            norm = np.where(norm < 0.1, 0.1, norm)
            norm = np.log10(norm)
            mn, mx = np.min(norm), np.max(norm)
            norm = (norm - mn) / (mx - mn + 1e-10)
        else:
            span = contrast_max - contrast_min + 1e-10
            norm = (norm - contrast_min) / span
        return norm

    @staticmethod
    def to_pil_image(
        img_data: np.ndarray,
        contrast_min: float,
        contrast_max: float,
        mode: str = "Linear",
        colormap: str = "灰度",
    ) -> Image.Image:
        norm = ImageRenderer.normalize(img_data, contrast_min, contrast_max, mode)
        h, w = norm.shape
        u8 = (norm * 255).astype(np.uint8)

        if colormap == "反转灰度":
            return Image.fromarray(255 - u8, mode='L').convert('RGB')

        if colormap == "热力图":
            rgb = np.zeros((h, w, 3), np.uint8)
            rgb[:, :, 0] = u8
            rgb[:, :, 1] = (128 * (1.0 - norm)).astype(np.uint8)
            rgb[:, :, 2] = (255 * (1.0 - norm)).astype(np.uint8)
            return Image.fromarray(rgb, mode='RGB')

        if colormap == "彩虹":
            rgb = np.zeros((h, w, 3), np.uint8)
            m1 = (norm >= 0)   & (norm < .25)
            m2 = (norm >= .25) & (norm < .5)
            m3 = (norm >= .5)  & (norm < .75)
            m4 = norm >= .75
            rgb[m1, 1] = (1020 * norm[m1]).astype(np.uint8); rgb[m1, 2] = 255
            rgb[m2, 1] = 255
            rgb[m2, 2] = (255 - 1020 * (norm[m2] - .25)).astype(np.uint8)
            rgb[m3, 0] = (1020 * (norm[m3] - .5)).astype(np.uint8); rgb[m3, 1] = 255
            rgb[m4, 0] = 255
            rgb[m4, 1] = (255 - 1020 * (norm[m4] - .75)).astype(np.uint8)
            return Image.fromarray(rgb, mode='RGB')

        # 默认灰度
        return Image.fromarray(u8, mode='L').convert('RGB')

    @staticmethod
    def mpl_cmap(colormap: str) -> str:
        return ImageRenderer.MPL_NAME.get(colormap, "gray")

    @staticmethod
    def to_png_b64(pil_img: Image.Image) -> str:
        buf = io.BytesIO()
        pil_img.save(buf, format='PNG', optimize=False)
        import base64
        return base64.b64encode(buf.getvalue()).decode('utf-8')


# ═══════════════════════════════════════════════════════════════════════════
# 像素坐标计算（原始衍射图）
# ═══════════════════════════════════════════════════════════════════════════

class PixelCoordinateCalculator:
    """
    将 (q Å⁻¹, ψ °) 坐标映射到原始衍射图像素坐标 (col, row)。

    ψ 旋转偏移的象限修正:
        Q1  sx=+1, sy=-1  →  使用 +rot_offset  (基准)
        Q2  sx=-1, sy=-1  →  使用 -rot_offset  (镜像 x)
        Q3  sx=-1, sy=+1  →  使用 +rot_offset  (双镜像)
        Q4  sx=+1, sy=+1  →  使用 -rot_offset  (镜像 y)
    统一公式: effective_rot = rot_offset * (-(sx * sy))
    """

    def __init__(self):
        self._invert_geom = None
        self._q_array = None
        self._chi_array = None
        self._ai = None
        self._wl   = 1.0
        self._px   = 100.0
        self._py   = 100.0
        self._cx   = 0.0
        self._cy   = 0.0
        self._dist = 1000.0
        self._quad = "第一象限"

    def set_pyfai_geometry(self, ai) -> None:
        if not PYFAI_OK:
            return
        try:
            self._invert_geom = InvertGeometry(ai)
        except Exception as e:
            print(f"[PixelCalc] Old InvertGeometry failed: {e}")
            self._invert_geom = None

    def set_pyfai_geometry_v2(self, ai) -> None:
        if not PYFAI_OK:
            return
        try:
            shape = ai.detector.shape
            if shape is None:
                print("[PixelCalc] Detector shape is None")
                return
            q_array = ai.qArray(shape)
            chi_array = ai.chiArray(shape)
            self._q_array = q_array
            self._chi_array = chi_array
            self._ai = ai
        except Exception as e:
            print(f"[PixelCalc] set_pyfai_geometry_v2 failed: {e}")
            self._q_array = None
            self._chi_array = None
            self._ai = None

    def set_manual_params(self, wl, px, py, cx, cy, dist) -> None:
        self._wl = wl; self._px = px; self._py = py
        self._cx = cx; self._cy = cy; self._dist = dist
        self._invert_geom = None
        self._q_array = None
        self._chi_array = None
        self._ai = None

    def set_quadrant(self, quad_text: str) -> None:
        self._quad = quad_text

    def get_center(self):
        return self._cx, self._cy

    def build_invert_geom_from_params(self) -> bool:
        if not PYFAI_OK:
            return False
        try:
            wl_m  = self._wl   * 1e-10
            px_m  = self._px   * 1e-6
            py_m  = self._py   * 1e-6
            dist_m = self._dist * 1e-3
            det = pyFAI.detector_factory('detector', config={'pixel1': py_m, 'pixel2': px_m})
            ai_tmp = AzimuthalIntegrator(
                dist=dist_m,
                poni1=self._cy * py_m,
                poni2=self._cx * px_m,
                detector=det,
                wavelength=wl_m,
            )
            self._invert_geom = InvertGeometry(ai_tmp)
            return True
        except Exception as e:
            print(f"[PixelCalc] build error: {e}")
            self._invert_geom = None
            return False

    def clear_invert_geom(self) -> None:
        self._invert_geom = None
        self._q_array = None
        self._chi_array = None
        self._ai = None

    @property
    def has_invert_geom(self) -> bool:
        return self._invert_geom is not None or self._q_array is not None

    def compute(self, q_ang: float, psi_deg: float, rot_offset: float = 0.0) -> Optional[tuple[int, int]]:
        quad = self._quad
        sx = 1  if "一" in quad or "四" in quad else -1
        sy = -1 if "一" in quad or "二" in quad else  1
        sign_corr = -(sx * sy)
        effective_psi = psi_deg + rot_offset * sign_corr

        if self._q_array is not None and self._chi_array is not None:
            try:
                result = self._compute_pyfai_v2(q_ang, effective_psi)
                if result is not None:
                    return result
            except Exception as e:
                print(f"[PixelCalc] pyFAI v2 compute failed: {e}")
        if PYFAI_OK and self._invert_geom is not None:
            try:
                result = self._compute_pyfai(q_ang, effective_psi)
                if result is not None:
                    return result
            except Exception:
                pass
        return self._compute_manual(q_ang, psi_deg, rot_offset)

    def _compute_pyfai(self, q_ang: float, psi_deg: float) -> Optional[tuple[int, int]]:
        q_nm = q_ang * 10.0
        chi  = math.radians(psi_deg)
        d0, d1 = self._invert_geom(
            np.array([q_nm], dtype=np.float64),
            np.array([chi],  dtype=np.float64),
            unit=pyFAI.units.Q_NM,
        )
        return int(round(float(d1[0]))), int(round(float(d0[0])))

    def _compute_pyfai_v2(self, q_ang: float, psi_deg: float) -> Optional[tuple[int, int]]:
        if self._q_array is None or self._chi_array is None:
            return None
        q_nm = q_ang * 10.0
        psi_rad = math.radians(psi_deg)
        diff_q = np.abs(self._q_array - q_nm)
        diff_chi = np.abs(self._chi_array - psi_rad)
        combined = diff_q + diff_chi * (q_nm * 0.01)
        idx = np.argmin(combined)
        result = np.unravel_index(idx, self._q_array.shape)
        return int(round(result[1])), int(round(result[0]))

    def _compute_manual(self, q_ang: float, psi_deg: float, rot_offset: float) -> Optional[tuple[int, int]]:
        try:
            quad = self._quad
            sx = 1  if "一" in quad or "四" in quad else -1
            sy = -1 if "一" in quad or "二" in quad else  1
            sign_corr = -(sx * sy)
            eff_psi   = psi_deg + rot_offset * sign_corr
            psi_rad   = math.radians(eff_psi)

            sin_theta = (q_ang * self._wl) / (4.0 * math.pi)
            if abs(sin_theta) > 1.0:
                return None
            theta = math.asin(sin_theta)
            r_mm  = self._dist * math.tan(2.0 * theta)

            x = self._cx + (sx * r_mm * math.cos(psi_rad) * 1000.0) / self._px
            y = self._cy + (sy * r_mm * math.sin(psi_rad) * 1000.0) / self._py
            return int(round(x)), int(round(y))
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════════════════
# ψ → 方位角映射（2D 积分图）
# ═══════════════════════════════════════════════════════════════════════════

class PsiAzimuthMapper:
    """将 Miller 文件中的 ψ 值映射到 2D 积分图像坐标系中的方位角"""

    def __init__(self, convention: str = "ccw", offset: float = 0.0):
        self.convention = convention
        self.offset     = offset

    def map(self, psi: float) -> float:
        az = (-psi + self.offset) if self.convention == "ccw" else (psi + self.offset)
        return AngleUtils.normalize_to_180(az)

    def map_miller_list(self, miller_raw: list[dict]) -> list[dict]:
        return [
            {
                'q':   pt['q'],
                'az':  self.map(pt['psi']),
                'hkl': f"({pt['h']},{pt['k']},{pt['l']})",
            }
            for pt in miller_raw
        ]


# ═══════════════════════════════════════════════════════════════════════════
# 原始图像标记绘制工具
# ═══════════════════════════════════════════════════════════════════════════

def draw_raw_markers(
    pil_img: Image.Image,
    full_pts: list[dict],
    output_pts: list[dict],
    cx: float, cy: float,
    show_labels: bool = True,
) -> Image.Image:
    """
    在 PIL Image 上绘制:
      · 黄色中心十字
      · 青色方块 (FullMiller)
      · 橙色菱形 (outputMiller)
      · Miller 指数标签（可选）
    """
    img = pil_img.convert('RGB')
    draw = ImageDraw.Draw(img)
    font = _ui_font(16)
    W, H = img.size
    full_pts = [p for p in full_pts if 0 <= p['x'] < W and 0 <= p['y'] < H]
    output_pts = [p for p in output_pts if 0 <= p['x'] < W and 0 <= p['y'] < H]

    # 中心十字（黄色）
    x0, y0 = int(round(cx)), int(round(cy))
    draw.line([(x0 - 14, y0), (x0 + 14, y0)], fill=(255, 255, 0), width=2)
    draw.line([(x0, y0 - 14), (x0, y0 + 14)], fill=(255, 255, 0), width=2)

    # ── FullMiller 青色方块 ──────────────────────────────────────────────
    CYAN   = (0, 210, 230)
    ORANGE = (255, 140, 0)

    def draw_square(x, y, color):
        draw.rectangle([x - 3, y - 3, x + 3, y + 3], outline=color, width=2)

    def draw_diamond(x, y, color):
        pts = [(x, y - 5), (x + 4, y), (x, y + 5), (x - 4, y)]
        draw.polygon(pts, outline=color)

    def draw_group(pts, color, draw_fn):
        groups: dict = {}
        for pt in pts:
            groups.setdefault((pt['x'], pt['y']), []).append(pt)
        for (x, y), group in groups.items():
            draw_fn(x, y, color)
            if show_labels:
                for i, pt in enumerate(group):
                    lbl = f"[{pt['h']}{pt['k']}{pt['l']}]"
                    draw.text((x - 14, y - 20 - i * 16), lbl, fill=color, font=font)

    draw_group(full_pts,   CYAN,   draw_square)
    draw_group(output_pts, ORANGE, draw_diamond)
    return img
