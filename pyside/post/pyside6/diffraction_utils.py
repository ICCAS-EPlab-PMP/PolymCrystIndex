#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diffraction_utils.py  —  后处理查看器工具库  v1.0  [PySide6 版]
将各核心功能封装为独立 class，供 UI 层调用。

模块说明:
  AngleUtils              — 角度归一化
  MillerFileParser        — 解析 FullMiller / outputMiller 文件
  InfoFileParser          — 解析 processing_info.txt (q/azimuth 范围)
  ColormapRenderer        — 将原始数组渲染为 QImage（线性/Log + 四种色表）
  PixelCoordinateCalculator — (q, ψ) → 像素坐标（pyFAI 或手动几何）
  PsiAzimuthMapper        — ψ → 图像方位角（2D 积分图用）
"""

from __future__ import annotations
import math, re
import numpy as np

# ── PySide6（替换 PyQt6）──────────────────────────────────────────────────────
from PySide6.QtGui import QImage

# ── pyFAI 可选 ──────────────────────────────────────────────────────────────
try:
    import pyFAI
    import pyFAI.units
    from pyFAI.ext.invert_geometry import InvertGeometry
    PYFAI_OK = True
except Exception:
    PYFAI_OK = False


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
    def parse(file_path: str) -> list[dict]:
        result = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [ln for ln in f.readlines() if ln.strip()]
            if not lines:
                return result

            # 判断第一行是否为纯数据行
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


# ═══════════════════════════════════════════════════════════════════════════
# 坐标信息文件解析
# ═══════════════════════════════════════════════════════════════════════════

class InfoFileParser:
    """解析 processing_info.txt，提取 q / azimuth 坐标范围"""

    @staticmethod
    def parse(file_path: str) -> dict | None:
        """返回 {'q_min', 'q_max', 'azimuth_min', 'azimuth_max'}，解析失败返回 None"""
        ranges: dict = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
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
        return ranges if ranges else None


# ═══════════════════════════════════════════════════════════════════════════
# 颜色映射渲染
# ═══════════════════════════════════════════════════════════════════════════

class ColormapRenderer:
    """
    将原始二维 numpy 数组渲染为 PySide6 QImage。
    支持线性 / Log 两种动态范围，以及四种色表。
    """

    # matplotlib 兼容名称映射（供 Integrated2DSimplePanel 使用）
    MPL_NAME: dict[str, str] = {
        "灰度": "gray", "反转灰度": "gray_r", "热力图": "hot", "彩虹": "jet"
    }

    @staticmethod
    def to_qimage(
        img_data: np.ndarray,
        contrast_min: float,
        contrast_max: float,
        mode: str = "Linear",
        colormap: str = "灰度",
    ) -> QImage:
        """
        Parameters
        ----------
        img_data     : 2-D float array
        contrast_min : 显示最小值
        contrast_max : 显示最大值
        mode         : "Linear" | "Log"
        colormap     : "灰度" | "反转灰度" | "热力图" | "彩虹"

        Returns
        -------
        QImage
        """
        norm = np.clip(img_data.astype(np.float64), contrast_min, contrast_max)

        if mode == "Log":
            norm = np.where(norm < 0.1, 0.1, norm)
            norm = np.log10(norm)
            mn, mx = np.min(norm), np.max(norm)
            norm = (norm - mn) / (mx - mn + 1e-10)
        else:
            span = contrast_max - contrast_min + 1e-10
            norm = (norm - contrast_min) / span

        h, w = norm.shape

        if colormap == "反转灰度":
            d = np.uint8(255 * (1.0 - norm))
            return QImage(d.tobytes(), w, h, w, QImage.Format.Format_Grayscale8)

        if colormap == "热力图":
            rgb = np.zeros((h, w, 3), np.uint8)
            rgb[:, :, 0] = np.uint8(255 * norm)
            rgb[:, :, 1] = np.uint8(128 * (1 - norm))
            rgb[:, :, 2] = np.uint8(255 * (1 - norm))
            return QImage(rgb.tobytes(), w, h, 3 * w, QImage.Format.Format_RGB888)

        if colormap == "彩虹":
            rgb = np.zeros((h, w, 3), np.uint8)
            m1 = (norm >= 0)   & (norm < .25)
            m2 = (norm >= .25) & (norm < .5)
            m3 = (norm >= .5)  & (norm < .75)
            m4 = norm >= .75
            rgb[m1, 1] = np.uint8(1020 * norm[m1]);            rgb[m1, 2] = 255
            rgb[m2, 1] = 255;  rgb[m2, 2] = np.uint8(255 - 1020 * (norm[m2] - .25))
            rgb[m3, 0] = np.uint8(1020 * (norm[m3] - .5));    rgb[m3, 1] = 255
            rgb[m4, 0] = 255;  rgb[m4, 1] = np.uint8(255 - 1020 * (norm[m4] - .75))
            return QImage(rgb.tobytes(), w, h, 3 * w, QImage.Format.Format_RGB888)

        # 默认：灰度
        d = np.uint8(255 * norm)
        return QImage(d.tobytes(), w, h, w, QImage.Format.Format_Grayscale8)

    @staticmethod
    def mpl_cmap(colormap: str) -> str:
        """返回 matplotlib colormap 字符串"""
        return ColormapRenderer.MPL_NAME.get(colormap, "gray")


# ═══════════════════════════════════════════════════════════════════════════
# 像素坐标计算（原始衍射图）
# ═══════════════════════════════════════════════════════════════════════════

class PixelCoordinateCalculator:
    """
    将 (q Å⁻¹, ψ °) 坐标映射到原始衍射图像素坐标 (col, row)。

    两种计算路径:
      1. pyFAI InvertGeometry — 精确，需要 poni 文件或正确手动参数
      2. 手动几何            — 近似，基于简单几何参数

    【ψ 旋转偏移的象限修正】
    在手动模式下，将 rot_offset 加到 ψ 角后再乘以 cos/sin，
    由于 sx/sy 对坐标轴的翻转，不同象限的旋转方向不一致。
    修正规则（以 Q1 为基准，视觉上正偏移 = 顺时针旋转）:

        Q1  sx=+1, sy=-1  →  sx·sy = -1  →  使用 +rot_offset  (基准)
        Q2  sx=-1, sy=-1  →  sx·sy = +1  →  使用 -rot_offset  (镜像 x)
        Q3  sx=-1, sy=+1  →  sx·sy = -1  →  使用 +rot_offset  (双镜像)
        Q4  sx=+1, sy=+1  →  sx·sy = +1  →  使用 -rot_offset  (镜像 y)

    统一公式: effective_rot = rot_offset * (-(sx * sy))
    """

    def __init__(self):
        self._invert_geom = None   # pyFAI InvertGeometry | None
        # 手动参数
        self._wl   = 1.0           # Å
        self._px   = 100.0         # μm
        self._py   = 100.0         # μm
        self._cx   = 0.0           # px
        self._cy   = 0.0           # px
        self._dist = 1000.0        # mm
        self._quad = "第一象限"

    # ── 设置接口 ─────────────────────────────────────────────────────────────

    def set_pyfai_geometry(self, ai) -> None:
        """从 AzimuthalIntegrator 构建 InvertGeometry"""
        if not PYFAI_OK:
            return
        self._invert_geom = InvertGeometry(ai)

    def set_invert_geom(self, ig) -> None:
        self._invert_geom = ig

    def set_manual_params(
        self,
        wl: float, px: float, py: float,
        cx: float, cy: float, dist: float,
    ) -> None:
        self._wl = wl; self._px = px; self._py = py
        self._cx = cx; self._cy = cy; self._dist = dist

    def set_quadrant(self, quad_text: str) -> None:
        self._quad = quad_text

    def build_invert_geom_from_params(self) -> bool:
        """用当前手动参数重建 InvertGeometry，成功返回 True"""
        if not PYFAI_OK:
            return False
        try:
            from pyFAI.detectors import Detector
            wl_m  = self._wl   * 1e-10
            px_m  = self._px   * 1e-6
            py_m  = self._py   * 1e-6
            dist_m = self._dist * 1e-3
            det = Detector(pixel1=py_m, pixel2=px_m)
            ai_tmp = pyFAI.AzimuthalIntegrator(
                dist=dist_m,
                poni1=self._cy * py_m,
                poni2=self._cx * px_m,
                detector=det,
                wavelength=wl_m,
            )
            self._invert_geom = InvertGeometry(ai_tmp)
            return True
        except Exception as e:
            print(f"[PixelCalc] build_invert_geom error: {e}")
            self._invert_geom = None
            return False

    def clear_invert_geom(self) -> None:
        self._invert_geom = None

    @property
    def has_invert_geom(self) -> bool:
        return self._invert_geom is not None

    # ── 计算接口 ─────────────────────────────────────────────────────────────

    def compute(
        self,
        q_ang: float,
        psi_deg: float,
        rot_offset: float = 0.0,
    ) -> tuple[int, int]:
        """
        计算像素坐标 (x=col, y=row)。
        rot_offset 以 Q1 为基准统一旋转方向。
        """
        # pyFAI 路径：直接加偏移，pyFAI 自己处理几何
        if PYFAI_OK and self._invert_geom is not None:
            try:
                result = self._compute_pyfai(q_ang, psi_deg + rot_offset)
                if result != (0, 0):
                    return result
            except Exception:
                pass
        # 手动路径：需要象限符号修正
        return self._compute_manual(q_ang, psi_deg, rot_offset)

    # ── 内部计算 ─────────────────────────────────────────────────────────────

    def _compute_pyfai(self, q_ang: float, psi_deg: float) -> tuple[int, int]:
        q_nm = q_ang * 10.0
        chi  = math.radians(psi_deg)
        d0, d1 = self._invert_geom(
            np.array([q_nm], dtype=np.float64),
            np.array([chi],  dtype=np.float64),
            unit=pyFAI.units.Q_NM,
        )
        return int(round(float(d1[0]))), int(round(float(d0[0])))

    def _compute_manual(
        self,
        q_ang: float,
        psi_deg: float,
        rot_offset: float,
    ) -> tuple[int, int]:
        try:
            quad = self._quad
            sx = 1  if "一" in quad or "四" in quad else -1
            sy = -1 if "一" in quad or "二" in quad else  1

            # ── 关键修正：以 Q1 为基准统一旋转方向 ──────────────────────────
            # Q1(sx·sy=-1) 为参考；Q2/Q4(sx·sy=+1) 需取反，消除镜像带来的方向反转
            sign_corr  = -(sx * sy)          # Q1→+1, Q2→-1, Q3→+1, Q4→-1
            eff_psi    = psi_deg + rot_offset * sign_corr
            psi_rad    = math.radians(eff_psi)

            sin_theta = (q_ang * self._wl) / (4.0 * math.pi)
            if abs(sin_theta) > 1.0:
                return 0, 0
            theta = math.asin(sin_theta)
            r_mm  = self._dist * math.tan(2.0 * theta)

            x = self._cx + (sx * r_mm * math.cos(psi_rad) * 1000.0) / self._px
            y = self._cy + (sy * r_mm * math.sin(psi_rad) * 1000.0) / self._py
            return int(round(x)), int(round(y))
        except Exception:
            return 0, 0


# ═══════════════════════════════════════════════════════════════════════════
# ψ → 方位角映射（2D 积分图）
# ═══════════════════════════════════════════════════════════════════════════

class PsiAzimuthMapper:
    """
    将 Miller 文件中的 ψ 值映射到 2D 积分图像坐标系中的方位角。

    convention : 'ccw' — 图像方位角与 ψ 反向（默认）
                 'cw'  — 图像方位角与 ψ 同向
    offset     : ψ=0 对应的图像 azimuth (°)
    """

    def __init__(self, convention: str = "ccw", offset: float = 0.0):
        self.convention = convention
        self.offset     = offset

    def map(self, psi: float) -> float:
        """单点映射，结果归一化到 (-180, 180]"""
        az = (-psi + self.offset) if self.convention == "ccw" else (psi + self.offset)
        return AngleUtils.normalize_to_180(az)

    def map_miller_list(self, miller_raw: list[dict]) -> list[dict]:
        """
        批量映射，输入 list of {h,k,l,q,psi}，
        返回 list of {q, az, hkl}
        """
        return [
            {
                'q':   pt['q'],
                'az':  self.map(pt['psi']),
                'hkl': f"({pt['h']},{pt['k']},{pt['l']})",
            }
            for pt in miller_raw
        ]
