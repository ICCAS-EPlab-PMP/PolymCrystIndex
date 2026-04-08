#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
post17.py   v3.1  [PySide6 版]
后处理查看器

【v3.1 修复与改进】
  1. 原始衍射图  — 新增「刷新视图」按钮，防止异常状态累积
  2. ψ 旋转偏移  — 修正 Q2/Q4 象限符号错误，现以 Q1 为基准统一旋转方向
  3. 原始衍射图  — 图像加载/刷新后自动居中
  4. 2D 积分图   — 导入坐标信息后强制重置视图范围，修复拉伸问题；
                   新增「刷新图像」按钮
  5. 代码结构    — 核心功能抽离到 diffraction_utils.py；界面层仅调用工具类

【工作流】
  第一步 — 选择数据来源:
    (A) 原始衍射图  (.tif / .edf / .cbf) → pyFAI InvertGeometry 映射到像素
    (B) 2D积分图像  (.npy / .tif)        → (q,ψ) 直接映射到积分图像坐标

  第二步 — 可选导入 Miller 文件:
    · FullMiller.txt   → 青色 (■) 标记
    · outputMiller.txt → 橙色 (◆) 标记
"""

import fabio
import numpy as np
import os
import sys

# ── PySide6（替换 PyQt6）──────────────────────────────────────────────────────
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QLineEdit, QMessageBox, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsTextItem,
    QComboBox, QSlider, QGroupBox, QSizePolicy, QFileDialog, QFormLayout,
    QDoubleSpinBox, QStatusBar,
    QRadioButton, QCheckBox, QStackedWidget, QButtonGroup, QFrame, QSpinBox,
)
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QPen, QColor, QFont, QAction, QPolygonF,
)
from PySide6.QtCore import Qt, QPointF, Signal, QRectF

import matplotlib
matplotlib.use("QtAgg")          # PySide6 使用 QtAgg 后端（替换 Qt5Agg）
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches

# ── 工具库 ───────────────────────────────────────────────────────────────────
from diffraction_utils import (
    PYFAI_OK,
    MillerFileParser,
    InfoFileParser,
    ColormapRenderer,
    PixelCoordinateCalculator,
    PsiAzimuthMapper,
)

# ── pyFAI 可选（仅用于加载 poni） ────────────────────────────────────────────
if PYFAI_OK:
    import pyFAI

# ═══════════════════════════════════════════════════════════════════════════
# 颜色常量
# ═══════════════════════════════════════════════════════════════════════════

_QCOLOR_FULL   = QColor(0, 210, 230)    # 青色  — FullMiller
_QCOLOR_OUTPUT = QColor(255, 140, 0)    # 橙色  — outputMiller
_MPL_FULL      = '#00d2e6'
_MPL_OUTPUT    = '#ff8c00'

# ═══════════════════════════════════════════════════════════════════════════
# 样式
# ═══════════════════════════════════════════════════════════════════════════

_BTN_QSS = """
QPushButton {
    background-color: #d0edff; color: #104fb9;
    border-radius: 8px; padding: 8px 14px; border: none;
    font-family: "Microsoft Yahei"; font-weight: bold; font-size: 12px;
}
QPushButton:hover   { background-color: #7ad6fb; }
QPushButton:pressed { background-color: #44bcf9; }
QPushButton:disabled{ background-color: #e0e0e0; color: #a0a0a0; }
"""

_BTN_REFRESH_QSS = """
QPushButton {
    background-color: #e0f7e0; color: #1a6b1a;
    border-radius: 8px; padding: 8px 14px; border: none;
    font-family: "Microsoft Yahei"; font-weight: bold; font-size: 12px;
}
QPushButton:hover   { background-color: #a8e6a8; }
QPushButton:pressed { background-color: #6fce6f; }
QPushButton:disabled{ background-color: #e0e0e0; color: #a0a0a0; }
"""

_GRP_QSS = """
QGroupBox {
    font-family: "Microsoft Yahei"; font-weight: bold; font-size: 13px;
    padding-top: 24px; margin-top: 1.5ex;
    border: 1px solid #7ad6fb; border-radius: 8px; background-color: transparent;
}
QGroupBox::title { color: #103d7e; subcontrol-position: top center; padding-top: 4px; }
QLabel   { color: #103d7e; font: bold 12px "Microsoft Yahei"; }
QLineEdit {
    color: #103d7e; background-color: white;
    font: bold 12px "Arial"; border: 1px solid #104fb9;
    border-radius: 2px; padding: 3px;
}
QPushButton {
    background-color: #d0edff; color: #104fb9;
    border-radius: 6px; padding: 6px 10px; border: none;
    font-family: "Microsoft Yahei"; font-weight: bold; font-size: 12px;
}
QPushButton:hover   { background-color: #7ad6fb; }
QPushButton:pressed { background-color: #44bcf9; }
QPushButton:disabled{ background-color: #e0e0e0; color: #a0a0a0; }
QComboBox { font: bold 12px "Microsoft Yahei"; color: #103d7e; }
"""

_SOURCE_BAR_QSS = """
QWidget#source_bar {
    background: #d8eeff;
    border-bottom: 2px solid #7ad6fb;
}
QLabel#src_title {
    color: #103d7e; font: bold 14px "Microsoft Yahei";
}
QRadioButton {
    color: #103d7e; font: bold 13px "Microsoft Yahei";
    padding: 6px 14px;
}
QRadioButton::indicator { width:16px; height:16px; }
"""


# ═══════════════════════════════════════════════════════════════════════════
# 面板 A — 原始衍射图
# ═══════════════════════════════════════════════════════════════════════════

class RawImagePanel(QWidget):
    """
    原始衍射图标记工具。
    · pyFAI InvertGeometry 将 (q, ψ) → 像素坐标
    · FullMiller → 青色方块  outputMiller → 橙色菱形
    · 两者可同时显示，也可各自清除
    · [v3.1] 新增刷新按钮；图像居中；ψ 旋转偏移象限修正
    """
    # PySide6 使用 Signal 替换 pyqtSignal
    status_msg = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.original_image = None
        self.display_image  = None
        self.image_height = self.image_width = 0

        # 像素坐标计算器（封装了 pyFAI 和手动几何）
        self._calc = PixelCoordinateCalculator()

        # pyFAI ai 备份（供状态显示）
        self._ai = None

        # Miller 数据
        self.full_miller_raw   = []
        self.output_miller_raw = []
        self.full_miller_pts   = []
        self.output_miller_pts = []

        self.contrast_min  = 0
        self.contrast_max  = 65535
        self.zoom_factor   = 0.4
        self._zoom_min = 0.01
        self._zoom_max = 10.0
        self._zoom_step = 0.1

        self._build_ui()

    # ──────────────────────────────────────── UI ────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # ── 左栏 ────────────────────────────────────────────────────────────
        left = QWidget()
        left.setMaximumWidth(400)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(4, 4, 4, 4)

        # 文件导入
        fg = QGroupBox("文件导入")
        fg.setStyleSheet(_GRP_QSS)
        fl = QVBoxLayout(fg)

        self.btn_image = QPushButton("① 导入衍射图像  (.tif / .edf / .cbf)")
        self.btn_image.setStyleSheet(_BTN_QSS)
        self.btn_image.clicked.connect(self.open_image_file)
        fl.addWidget(self.btn_image)

        self.btn_poni = QPushButton("② 导入 PONI 文件（推荐，自动填参）")
        self.btn_poni.setStyleSheet(_BTN_QSS)
        self.btn_poni.setEnabled(False)
        self.btn_poni.clicked.connect(self.import_poni_file)
        fl.addWidget(self.btn_poni)

        # Miller 导入
        miller_row = QHBoxLayout()
        self.btn_full   = QPushButton("导入 FullMiller ■")
        self.btn_output = QPushButton("导入 outputMiller ◆")
        self.btn_full.setStyleSheet(
            _BTN_QSS.replace("#d0edff", "#cffafe").replace("#104fb9", "#0e7490"))
        self.btn_output.setStyleSheet(
            _BTN_QSS.replace("#d0edff", "#fff3cd").replace("#104fb9", "#92400e"))
        for b in (self.btn_full, self.btn_output):
            b.setEnabled(False)
            miller_row.addWidget(b)
        self.btn_full.clicked.connect(lambda: self._import_miller_dialog("full"))
        self.btn_output.clicked.connect(lambda: self._import_miller_dialog("output"))
        fl.addLayout(miller_row)

        # 状态标签
        stat_row = QHBoxLayout()
        self.lbl_full_stat   = QLabel("FullMiller: 未加载")
        self.lbl_output_stat = QLabel("outputMiller: 未加载")
        self.lbl_full_stat.setStyleSheet("color:#0e7490;font:italic bold 11px 'Arial';")
        self.lbl_output_stat.setStyleSheet("color:#92400e;font:italic bold 11px 'Arial';")
        stat_row.addWidget(self.lbl_full_stat)
        stat_row.addWidget(self.lbl_output_stat)
        fl.addLayout(stat_row)

        # 操作行
        act_row = QHBoxLayout()
        self.btn_save      = QPushButton("保存标记图像")
        self.btn_clear_all = QPushButton("清除全部标记")
        for b in (self.btn_save, self.btn_clear_all):
            b.setStyleSheet(_BTN_QSS)
            b.setEnabled(False)
            act_row.addWidget(b)
        self.btn_save.clicked.connect(self.save_marked_image)
        self.btn_clear_all.clicked.connect(self.clear_all_miller)
        fl.addLayout(act_row)
        lv.addWidget(fg)

        # 仪器参数
        pg = QGroupBox("仪器参数（无 PONI 时手动填入）")
        pg.setStyleSheet(_GRP_QSS)
        pv = QVBoxLayout(pg)

        poni_row = QHBoxLayout()
        poni_row.addWidget(QLabel("PONI状态:"))
        self.lbl_poni = QLabel("未加载")
        self.lbl_poni.setStyleSheet("color:#cc6600;font-weight:bold;")
        poni_row.addWidget(self.lbl_poni)
        pv.addLayout(poni_row)

        self.edt_wl   = self._param_row(pv, "波长 (Å):",          "1.0")
        self.edt_px   = self._param_row(pv, "像素 X (μm):",        "100")
        self.edt_py   = self._param_row(pv, "像素 Y (μm):",        "100")
        self.edt_cx   = self._param_row(pv, "中心 X (px):",        "0")
        self.edt_cy   = self._param_row(pv, "中心 Y (px):",        "0")
        self.edt_dist = self._param_row(pv, "探测器距离 (mm):",    "1000")
        self.edt_rot  = self._param_row(pv, "ψ 旋转偏移 (°):",     "0.0")

        for edt in (self.edt_wl, self.edt_px, self.edt_py,
                    self.edt_cx, self.edt_cy, self.edt_dist, self.edt_rot):
            edt.editingFinished.connect(self._on_params_changed)
        lv.addWidget(pg)

        # 对比度
        cg = QGroupBox("对比度 & 显示")
        cg.setStyleSheet(_GRP_QSS)
        cv = QVBoxLayout(cg)

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("模式:"))
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["Linear", "Log"])
        self.cmb_mode.currentIndexChanged.connect(self._refresh_image)
        r1.addWidget(self.cmb_mode)
        r1.addWidget(QLabel("颜色:"))
        self.cmb_cmap = QComboBox()
        self.cmb_cmap.addItems(["灰度", "反转灰度", "热力图", "彩虹"])
        self.cmb_cmap.currentIndexChanged.connect(self._refresh_image)
        r1.addWidget(self.cmb_cmap)
        cv.addLayout(r1)

        r2h = QHBoxLayout()
        r2h.addWidget(QLabel("Min:"))
        self.spin_min = QSpinBox(); self.spin_min.setRange(0, 65535)
        self.spin_min.setValue(0);   self.spin_min.setFixedWidth(78)
        self.spin_min.setStyleSheet("color:#104fb9;font:bold 11px 'Arial';")
        self.sld_min  = QSlider(Qt.Orientation.Horizontal)
        self.sld_min.setRange(0, 65535); self.sld_min.setValue(0)
        self.spin_min.valueChanged.connect(self._on_contrast_changed)
        self.sld_min.valueChanged.connect(self._on_contrast_changed)
        r2h.addWidget(self.spin_min); r2h.addWidget(self.sld_min)
        cv.addLayout(r2h)

        r3h = QHBoxLayout()
        r3h.addWidget(QLabel("Max:"))
        self.spin_max = QSpinBox(); self.spin_max.setRange(0, 65535)
        self.spin_max.setValue(65535); self.spin_max.setFixedWidth(78)
        self.spin_max.setStyleSheet("color:#104fb9;font:bold 11px 'Arial';")
        self.sld_max  = QSlider(Qt.Orientation.Horizontal)
        self.sld_max.setRange(0, 65535); self.sld_max.setValue(65535)
        self.spin_max.valueChanged.connect(self._on_contrast_changed)
        self.sld_max.valueChanged.connect(self._on_contrast_changed)
        r3h.addWidget(self.spin_max); r3h.addWidget(self.sld_max)
        cv.addLayout(r3h)
        lv.addWidget(cg)

        # 显示控制
        dg = QGroupBox("显示控制")
        dg.setStyleSheet(_GRP_QSS)
        dv = QVBoxLayout(dg)

        # [v3.1] 刷新按钮 —— 防止因异常操作导致的显示错乱
        self.btn_refresh = QPushButton("⟳ 刷新视图（居中 & 重置缩放）")
        self.btn_refresh.setStyleSheet(_BTN_REFRESH_QSS)
        self.btn_refresh.clicked.connect(self._refresh_view)
        dv.addWidget(self.btn_refresh)

        btn_zoom = QPushButton("重置缩放 (0.4×)")
        btn_zoom.setStyleSheet(_BTN_QSS)
        btn_zoom.clicked.connect(self.reset_zoom)
        dv.addWidget(btn_zoom)

        self.chk_labels = QCheckBox("显示 Miller 标签")
        self.chk_labels.setChecked(True)
        self.chk_labels.stateChanged.connect(self._refresh_image)
        dv.addWidget(self.chk_labels)

        qrow = QHBoxLayout()
        qrow.addWidget(QLabel("象限:"))
        self.cmb_quad = QComboBox()
        self.cmb_quad.addItems(["第一象限", "第二象限", "第三象限", "第四象限"])
        self.cmb_quad.currentIndexChanged.connect(self._on_quad_changed)
        qrow.addWidget(self.cmb_quad)
        dv.addLayout(qrow)

        # 图例
        leg_row = QHBoxLayout()
        lbl_f = QLabel("■  FullMiller")
        lbl_f.setStyleSheet("color:#0e7490; font:bold 11px 'Arial';")
        lbl_o = QLabel("◆  outputMiller")
        lbl_o.setStyleSheet("color:#92400e; font:bold 11px 'Arial';")
        leg_row.addWidget(lbl_f); leg_row.addWidget(lbl_o)
        dv.addLayout(leg_row)

        lv.addWidget(dg)
        lv.addStretch()

        # ── 右栏 — 图像显示 ─────────────────────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)

        vg = QGroupBox("图像显示")
        vg.setStyleSheet(_GRP_QSS)
        vgl = QVBoxLayout(vg)

        self.scene = QGraphicsScene()
        self.view  = QGraphicsView(self.scene)
        self.view.setMouseTracking(True)
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.view.wheelEvent = self._wheel_event
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        # 对齐方式：使内容在视口内居中
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vgl.addWidget(self.view)
        rv.addWidget(vg)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(
            "background:#ebfaff;color:#103d7e;border-top:1px solid #7096D1;font-size:12px;")
        rv.addWidget(self.status_bar)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([380, 850])

        # 初始化缩放（此时 scene 还是空的，不需要居中）
        self.view.resetTransform()
        self.view.scale(self.zoom_factor, self.zoom_factor)

    def _param_row(self, parent_layout, label, default):
        row = QHBoxLayout()
        lbl = QLabel(label); lbl.setMinimumWidth(150)
        edt = QLineEdit(default); edt.setFixedWidth(110)
        row.addWidget(lbl); row.addWidget(edt); row.addStretch()
        parent_layout.addLayout(row)
        return edt

    # ──────────────────────────────────────── 槽 ────────────────────────────
    def _set_status(self, msg: str):
        self.status_bar.showMessage(msg)
        self.status_msg.emit(msg)

    def open_image_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入衍射图像", "",
            "衍射图像 (*.tif *.tiff *.edf *.cbf *.img);;All Files (*)")
        if not path:
            return
        try:
            self.original_image = fabio.open(path).data
            self.display_image  = self.original_image.copy()
            self.image_height, self.image_width = self.display_image.shape
            self._auto_contrast()
            self.btn_poni.setEnabled(True)
            self.btn_full.setEnabled(True)
            self.btn_output.setEnabled(True)
            self.btn_save.setEnabled(False)
            self.btn_clear_all.setEnabled(False)
            self.full_miller_raw   = []; self.output_miller_raw = []
            self.full_miller_pts   = []; self.output_miller_pts = []
            self.lbl_full_stat.setText("FullMiller: 未加载")
            self.lbl_output_stat.setText("outputMiller: 未加载")
            # [v3.1] 先渲染图像，再重置缩放和居中
            self._refresh_image()
            self.reset_zoom()
            self._set_status(
                f"已加载: {os.path.basename(path)}  ({self.image_width}×{self.image_height})")
        except Exception as e:
            self._set_status(f"加载错误: {e}")

    def _auto_contrast(self):
        if self.original_image is None:
            return
        flat = self.original_image.flatten()
        cmin = int(np.min(flat))
        cmax_full = int(np.max(flat))
        if flat.size > 50:
            top50 = np.partition(flat, -50)[-50:]
            cmax = int((np.median(top50) + np.max(top50)) / 2)
        else:
            cmax = cmax_full
        for w in (self.sld_min, self.sld_max, self.spin_min, self.spin_max):
            w.blockSignals(True)
            w.setRange(cmin, cmax_full)
            w.blockSignals(False)
        self.sld_min.setValue(cmin);  self.spin_min.setValue(cmin)
        self.sld_max.setValue(cmax);  self.spin_max.setValue(cmax)
        self.contrast_min = cmin; self.contrast_max = cmax

    def import_poni_file(self):
        if not PYFAI_OK:
            self._set_status("错误: 未找到 pyFAI，无法加载 PONI 文件")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "导入 PONI 文件", "", "PONI Files (*.poni);;All Files (*)")
        if not path:
            return
        try:
            ai = pyFAI.load(path)
            self._ai = ai
            px = ai.detector.pixel2 * 1e6 if hasattr(ai.detector, 'pixel2') else 100.0
            py = ai.detector.pixel1 * 1e6 if hasattr(ai.detector, 'pixel1') else 100.0
            cx = ai.poni2 / (ai.detector.pixel2 or 1e-6)
            cy = ai.poni1 / (ai.detector.pixel1 or 1e-6)
            self.edt_wl.setText(f"{ai.wavelength*1e10:.6f}")
            self.edt_px.setText(f"{px:.2f}"); self.edt_py.setText(f"{py:.2f}")
            self.edt_cx.setText(f"{cx:.2f}"); self.edt_cy.setText(f"{cy:.2f}")
            self.edt_dist.setText(f"{ai.dist*1e3:.2f}")
            # 更新计算器
            self._calc.set_pyfai_geometry(ai)
            self.lbl_poni.setText(f"✓ {os.path.basename(path)}")
            self.lbl_poni.setStyleSheet("color:#006600;font-weight:bold;")
            self._set_status(f"PONI 已加载: {os.path.basename(path)}")
            self.recalculate_all_points()
        except Exception as e:
            self._set_status(f"PONI 加载错误: {e}")

    def _import_miller_dialog(self, source: str):
        label = "FullMiller" if source == "full" else "outputMiller"
        path, _ = QFileDialog.getOpenFileName(
            self, f"导入 {label}.txt", "", f"{label} (*.txt);;All Files (*)")
        if not path:
            return

        data = MillerFileParser.parse(path)
        if not data:
            self._set_status(f"错误: 无法从 {os.path.basename(path)} 解析有效数据")
            return

        if source == "full":
            self.full_miller_raw = data
            self.lbl_full_stat.setText(f"FullMiller: {len(data)} 点")
        else:
            self.output_miller_raw = data
            self.lbl_output_stat.setText(f"outputMiller: {len(data)} 点")

        # 若尚无 pyFAI 几何，尝试从手动参数构建
        if PYFAI_OK and not self._calc.has_invert_geom:
            self._sync_manual_params_to_calc()
            self._calc.build_invert_geom_from_params()

        self.recalculate_all_points()
        has_any = bool(self.full_miller_pts or self.output_miller_pts)
        self.btn_save.setEnabled(has_any)
        self.btn_clear_all.setEnabled(has_any)
        self._set_status(f"已导入 {len(data)} 个 {label} 点 ← {os.path.basename(path)}")

    # ──────────────────────────────────────── 参数同步 ───────────────────────
    def _sync_manual_params_to_calc(self):
        """将 UI 参数字段同步到计算器"""
        try:
            self._calc.set_manual_params(
                wl   = float(self.edt_wl.text()),
                px   = float(self.edt_px.text()),
                py   = float(self.edt_py.text()),
                cx   = float(self.edt_cx.text()),
                cy   = float(self.edt_cy.text()),
                dist = float(self.edt_dist.text()),
            )
            self._calc.set_quadrant(self.cmb_quad.currentText())
        except ValueError:
            pass

    def _on_params_changed(self):
        self._sync_manual_params_to_calc()
        # 手动参数改变时，若使用的是手动构建的 InvertGeometry，需要重建
        if PYFAI_OK and self._ai is None:
            self._calc.build_invert_geom_from_params()
        self.recalculate_all_points()

    def _on_quad_changed(self):
        """象限切换：同步到计算器，重新计算"""
        self._calc.set_quadrant(self.cmb_quad.currentText())
        self.recalculate_all_points()

    # ──────────────────────────────────────── 坐标计算 ───────────────────────
    def recalculate_all_points(self):
        try:
            rot_offset = float(self.edt_rot.text())
        except ValueError:
            rot_offset = 0.0

        self._sync_manual_params_to_calc()

        self.full_miller_pts = []
        for pt in self.full_miller_raw:
            # [v3.1] rot_offset 由 PixelCoordinateCalculator 统一处理象限修正
            x, y = self._calc.compute(pt['q'], pt['psi'], rot_offset)
            self.full_miller_pts.append(
                {'h': pt['h'], 'k': pt['k'], 'l': pt['l'], 'x': x, 'y': y})

        self.output_miller_pts = []
        for pt in self.output_miller_raw:
            x, y = self._calc.compute(pt['q'], pt['psi'], rot_offset)
            self.output_miller_pts.append(
                {'h': pt['h'], 'k': pt['k'], 'l': pt['l'], 'x': x, 'y': y})

        self._refresh_image()

    # ──────────────────────────────────────── 渲染 ───────────────────────────
    def _refresh_image(self):
        """重新渲染图像到 scene（不改变缩放/平移）"""
        self.scene.clear()
        if self.display_image is None:
            return
        qimg   = ColormapRenderer.to_qimage(
            self.display_image,
            self.contrast_min, self.contrast_max,
            self.cmb_mode.currentText(),
            self.cmb_cmap.currentText(),
        )
        pixmap = QPixmap.fromImage(qimg)
        item   = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(item)
        # [v3.1] 设置 sceneRect = 图像范围，防止滚动区域偏移
        self.scene.setSceneRect(QRectF(0, 0, self.image_width, self.image_height))
        self._draw_miller_markers()

    def _refresh_view(self):
        """
        [v3.1] 刷新视图：重新计算 Miller 点 + 重新渲染 + 重置缩放 + 居中。
        用于在出现显示异常时手动恢复正常状态；同时自动重新加载 FullMiller / outputMiller。
        """
        # recalculate_all_points 内部已调用 _refresh_image，无需单独调用
        self.recalculate_all_points()
        self.reset_zoom()
        self._set_status("视图已刷新，Miller 点已重新计算并居中")

    def _draw_miller_markers(self):
        show_lbl = self.chk_labels.isChecked()
        font = QFont("Arial", 9, QFont.Weight.Bold)

        # 中心十字
        try:
            cx = float(self.edt_cx.text())
            cy = float(self.edt_cy.text())
            yp = QPen(QColor(255, 255, 0), 2)
            self.scene.addLine(cx-12, cy,    cx+12, cy,    yp)
            self.scene.addLine(cx,    cy-12, cx,    cy+12, yp)
        except Exception:
            pass

        def draw_square(x, y, pen):
            self.scene.addRect(x-3, y-3, 6, 6, pen)

        def draw_diamond(x, y, pen):
            poly = QPolygonF([
                QPointF(x,   y-5),
                QPointF(x+4, y),
                QPointF(x,   y+5),
                QPointF(x-4, y),
            ])
            self.scene.addPolygon(poly, pen)

        def draw_group(pts, color, draw_fn):
            pen = QPen(color, 2)
            groups = {}
            for pt in pts:
                groups.setdefault((pt['x'], pt['y']), []).append(pt)
            for (x, y), group in groups.items():
                draw_fn(x, y, pen)
                if show_lbl:
                    for i, pt in enumerate(group):
                        txt   = f"[{pt['h']}{pt['k']}{pt['l']}]"
                        titem = QGraphicsTextItem(txt)
                        titem.setDefaultTextColor(color)
                        titem.setFont(font)
                        tw = titem.boundingRect().width()
                        titem.setPos(x - tw/2, y - 20 - i*18)
                        self.scene.addItem(titem)

        draw_group(self.full_miller_pts,   _QCOLOR_FULL,   draw_square)
        draw_group(self.output_miller_pts, _QCOLOR_OUTPUT, draw_diamond)

    # ──────────────────────────────────────── 清除 & 保存 ────────────────────
    def clear_all_miller(self):
        self.full_miller_raw   = []; self.output_miller_raw = []
        self.full_miller_pts   = []; self.output_miller_pts = []
        self.lbl_full_stat.setText("FullMiller: 未加载")
        self.lbl_output_stat.setText("outputMiller: 未加载")
        self._refresh_image()
        self.btn_save.setEnabled(False)
        self.btn_clear_all.setEnabled(False)
        self._set_status("已清除所有标记点")

    def save_marked_image(self):
        if not (self.full_miller_pts or self.output_miller_pts):
            self._set_status("错误: 没有标记点")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存标记图像", "", "PNG (*.png)")
        if not path:
            return
        try:
            pixmap  = QPixmap(self.image_width, self.image_height)
            pixmap.fill(Qt.GlobalColor.white)
            painter = QPainter(pixmap)
            painter.drawImage(0, 0, ColormapRenderer.to_qimage(
                self.display_image, self.contrast_min, self.contrast_max,
                self.cmb_mode.currentText(), self.cmb_cmap.currentText()))

            try:
                cx = float(self.edt_cx.text()); cy = float(self.edt_cy.text())
                painter.setPen(QPen(QColor(255, 255, 0), 2))
                painter.drawLine(int(cx-12), int(cy),    int(cx+12), int(cy))
                painter.drawLine(int(cx),    int(cy-12), int(cx),    int(cy+12))
            except Exception:
                pass

            show_lbl = self.chk_labels.isChecked()
            font = QFont("Arial", 9, QFont.Weight.Bold)
            painter.setFont(font)

            def paint_square(px_, py_, color):
                painter.setPen(QPen(color, 2))
                painter.drawRect(int(px_-3), int(py_-3), 6, 6)

            def paint_diamond(px_, py_, color):
                painter.setPen(QPen(color, 2))
                pts = [QPointF(px_, py_-5), QPointF(px_+4, py_),
                       QPointF(px_, py_+5), QPointF(px_-4, py_)]
                painter.drawPolygon(QPolygonF(pts))

            def paint_group(pts, color, draw_fn):
                groups = {}
                for pt in pts:
                    groups.setdefault((pt['x'], pt['y']), []).append(pt)
                for (x, y), group in groups.items():
                    draw_fn(x, y, color)
                    if show_lbl:
                        for i, pt in enumerate(group):
                            txt = f"[{pt['h']}{pt['k']}{pt['l']}]"
                            tw  = painter.fontMetrics().horizontalAdvance(txt)
                            painter.setPen(QPen(color, 1))
                            painter.drawText(int(x - tw/2), int(y - 6 - i*18), txt)

            paint_group(self.full_miller_pts,   _QCOLOR_FULL,   paint_square)
            paint_group(self.output_miller_pts, _QCOLOR_OUTPUT, paint_diamond)
            painter.end()
            pixmap.save(path, "PNG", 600)
            self._set_status(f"已保存: {path}")
        except Exception as e:
            self._set_status(f"保存错误: {e}")

    # ──────────────────────────────────────── 对比度 ─────────────────────────
    def _on_contrast_changed(self):
        s = self.sender()
        if s is self.sld_min:
            self.spin_min.blockSignals(True); self.spin_min.setValue(self.sld_min.value()); self.spin_min.blockSignals(False)
        elif s is self.spin_min:
            self.sld_min.blockSignals(True);  self.sld_min.setValue(self.spin_min.value());  self.sld_min.blockSignals(False)
        elif s is self.sld_max:
            self.spin_max.blockSignals(True); self.spin_max.setValue(self.sld_max.value()); self.spin_max.blockSignals(False)
        elif s is self.spin_max:
            self.sld_max.blockSignals(True);  self.sld_max.setValue(self.spin_max.value());  self.sld_max.blockSignals(False)
        self.contrast_min = self.spin_min.value()
        self.contrast_max = self.spin_max.value()
        self._refresh_image()

    # ──────────────────────────────────────── 缩放 & 居中 ────────────────────
    def reset_zoom(self):
        """[v3.1] 重置缩放并将图像居中于视口"""
        self.zoom_factor = 0.4
        self.view.resetTransform()
        self.view.scale(self.zoom_factor, self.zoom_factor)
        # 居中到 scene 中心
        if self.image_width > 0 and self.image_height > 0:
            self.view.centerOn(self.image_width / 2, self.image_height / 2)

    def _wheel_event(self, event):
        if self.original_image is None:
            return
        if event.angleDelta().y() > 0:
            self.zoom_factor = min(self.zoom_factor * (1 + self._zoom_step), self._zoom_max)
        else:
            self.zoom_factor = max(self.zoom_factor * (1 - self._zoom_step), self._zoom_min)
        self.view.resetTransform()
        self.view.scale(self.zoom_factor, self.zoom_factor)
        self._set_status(f"缩放: {self.zoom_factor:.2f}×")


# ═══════════════════════════════════════════════════════════════════════════
# 面板 B — 2D 积分图像
# ═══════════════════════════════════════════════════════════════════════════

class Integrated2DSimplePanel(QWidget):
    """
    2D 积分图像 Miller 点叠加工具。
    · 加载 .npy / .tif 积分图
    · 直接将 (q, ψ) 用坐标范围映射到图像坐标
    · [v3.1] 导入坐标信息后强制重置视图范围（修复拉伸）
    · [v3.1] 新增「刷新图像」按钮
    """
    # PySide6 使用 Signal 替换 pyqtSignal
    status_msg = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.image_data    = None
        self.q_range       = (0.0, 1.0)
        self.azimuth_range = (-180.0, 180.0)

        self.contrast_min     = 0
        self.contrast_max     = 65535
        self.current_colormap = "灰度"

        self.full_miller_raw    = []
        self.output_miller_raw  = []
        self.full_miller_mapped   = []
        self.output_miller_mapped = []

        # ψ → Azimuth 映射器
        self._mapper = PsiAzimuthMapper(convention="ccw", offset=0.0)

        self.az_crop_enabled = False
        self.az_crop_min     = -10.0
        self.az_crop_max     = 120.0

        self._build_ui()

    # ──────────────────────────────────────── UI ────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # ── 左栏 ─────────────────────────────────────────────────────────────
        left = QWidget()
        left.setMaximumWidth(360)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(4, 4, 4, 4)

        # 文件导入
        fg = QGroupBox("文件导入")
        fg.setStyleSheet(_GRP_QSS)
        fl = QVBoxLayout(fg)

        self.btn_open = QPushButton("① 导入 2D积分图像  (.npy / .tif)")
        self.btn_open.setStyleSheet(_BTN_QSS)
        self.btn_open.clicked.connect(self.open_image_file)
        fl.addWidget(self.btn_open)

        self.btn_info = QPushButton("② 导入坐标信息文件  (processing_info.txt)")
        self.btn_info.setStyleSheet(_BTN_QSS)
        self.btn_info.clicked.connect(self.import_info_file)
        fl.addWidget(self.btn_info)

        # [v3.1] 刷新按钮 — 重置视图及重新渲染，修复拉伸/偏移等异常显示
        self.btn_refresh_2d = QPushButton("⟳ 刷新图像（重置视图）")
        self.btn_refresh_2d.setStyleSheet(_BTN_REFRESH_QSS)
        self.btn_refresh_2d.clicked.connect(self._refresh_full)
        fl.addWidget(self.btn_refresh_2d)

        miller_row = QHBoxLayout()
        self.btn_full   = QPushButton("导入 FullMiller ●")
        self.btn_output = QPushButton("导入 outputMiller ◆")
        self.btn_full.setStyleSheet(
            _BTN_QSS.replace("#d0edff", "#cffafe").replace("#104fb9", "#0e7490"))
        self.btn_output.setStyleSheet(
            _BTN_QSS.replace("#d0edff", "#fff3cd").replace("#104fb9", "#92400e"))
        miller_row.addWidget(self.btn_full)
        miller_row.addWidget(self.btn_output)
        self.btn_full.clicked.connect(lambda: self._import_miller_dialog("full"))
        self.btn_output.clicked.connect(lambda: self._import_miller_dialog("output"))
        fl.addLayout(miller_row)

        stat_row = QHBoxLayout()
        self.lbl_full_stat   = QLabel("FullMiller: 未加载")
        self.lbl_output_stat = QLabel("outputMiller: 未加载")
        self.lbl_full_stat.setStyleSheet("color:#0e7490;font:italic bold 11px 'Arial';")
        self.lbl_output_stat.setStyleSheet("color:#92400e;font:italic bold 11px 'Arial';")
        stat_row.addWidget(self.lbl_full_stat)
        stat_row.addWidget(self.lbl_output_stat)
        fl.addLayout(stat_row)

        act_row = QHBoxLayout()
        self.btn_save  = QPushButton("保存标记图像")
        self.btn_clear = QPushButton("清除标记")
        for b in (self.btn_save, self.btn_clear):
            b.setStyleSheet(_BTN_QSS)
            act_row.addWidget(b)
        self.btn_save.clicked.connect(self.save_marked_image)
        self.btn_clear.clicked.connect(self.clear_all_miller)
        fl.addLayout(act_row)
        lv.addWidget(fg)

        # 坐标范围
        rg = QGroupBox("坐标范围")
        rg.setStyleSheet(_GRP_QSS)
        rf = QFormLayout(rg)
        self.q_min_edt  = QLineEdit("0.0")
        self.q_max_edt  = QLineEdit("1.0")
        self.az_min_edt = QLineEdit("-180.0")
        self.az_max_edt = QLineEdit("180.0")
        apply_btn = QPushButton("应用坐标范围")
        apply_btn.setStyleSheet(_BTN_QSS)
        apply_btn.clicked.connect(self.update_coordinate_ranges)
        rf.addRow("q Min (Å⁻¹):",    self.q_min_edt)
        rf.addRow("q Max (Å⁻¹):",    self.q_max_edt)
        rf.addRow("方位角 Min (°):", self.az_min_edt)
        rf.addRow("方位角 Max (°):", self.az_max_edt)
        rf.addRow(apply_btn)
        lv.addWidget(rg)

        # 对比度
        cg = QGroupBox("对比度 & 颜色")
        cg.setStyleSheet(_GRP_QSS)
        cv = QVBoxLayout(cg)

        cm_row = QHBoxLayout()
        cm_row.addWidget(QLabel("颜色:"))
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(["灰度", "反转灰度", "热力图", "彩虹"])
        self.cmap_combo.currentIndexChanged.connect(self._on_cmap_changed)
        cm_row.addWidget(self.cmap_combo)
        cv.addLayout(cm_row)

        r2h = QHBoxLayout()
        r2h.addWidget(QLabel("Min:"))
        self.spin_min = QSpinBox(); self.spin_min.setRange(0, 65535)
        self.spin_min.setValue(0);  self.spin_min.setFixedWidth(78)
        self.spin_min.setStyleSheet("color:#104fb9;font:bold 11px 'Arial';")
        self.sld_min  = QSlider(Qt.Orientation.Horizontal)
        self.sld_min.setRange(0, 65535); self.sld_min.setValue(0)
        self.spin_min.valueChanged.connect(self._on_contrast_changed)
        self.sld_min.valueChanged.connect(self._on_contrast_changed)
        r2h.addWidget(self.spin_min); r2h.addWidget(self.sld_min)
        cv.addLayout(r2h)

        r3h = QHBoxLayout()
        r3h.addWidget(QLabel("Max:"))
        self.spin_max = QSpinBox(); self.spin_max.setRange(0, 65535)
        self.spin_max.setValue(65535); self.spin_max.setFixedWidth(78)
        self.spin_max.setStyleSheet("color:#104fb9;font:bold 11px 'Arial';")
        self.sld_max  = QSlider(Qt.Orientation.Horizontal)
        self.sld_max.setRange(0, 65535); self.sld_max.setValue(65535)
        self.spin_max.valueChanged.connect(self._on_contrast_changed)
        self.sld_max.valueChanged.connect(self._on_contrast_changed)
        r3h.addWidget(self.spin_max); r3h.addWidget(self.sld_max)
        cv.addLayout(r3h)
        lv.addWidget(cg)

        # Miller 坐标映射
        mg = QGroupBox("Miller 坐标映射 (ψ → 图像 Azimuth)")
        mg.setStyleSheet(_GRP_QSS)
        mf = QFormLayout(mg)

        self.conv_combo = QComboBox()
        self.conv_combo.addItem("图像 Azimuth 与 ψ 同向 (CCW)", "cw")
        self.conv_combo.addItem("图像 Azimuth 与 ψ 反向 (CW)", "ccw")
        self.conv_combo.setCurrentIndex(1)
        self.conv_combo.currentIndexChanged.connect(self._on_miller_settings_changed)
        mf.addRow("ψ 约定:", self.conv_combo)

        self.offset_spin = QDoubleSpinBox()
        self.offset_spin.setSuffix(" °"); self.offset_spin.setRange(-360.0, 360.0)
        self.offset_spin.setValue(0.0); self.offset_spin.setSingleStep(1.0)
        self.offset_spin.valueChanged.connect(self._on_miller_settings_changed)
        mf.addRow("ψ=0 对应图像 Azimuth (°):", self.offset_spin)

        leg_row = QHBoxLayout()
        lbl_f = QLabel("●  FullMiller (青色)")
        lbl_f.setStyleSheet("color:#0e7490;font:bold 11px 'Arial';")
        lbl_o = QLabel("◆  outputMiller (橙色)")
        lbl_o.setStyleSheet("color:#92400e;font:bold 11px 'Arial';")
        leg_row.addWidget(lbl_f); leg_row.addWidget(lbl_o)
        mf.addRow(leg_row)
        lv.addWidget(mg)

        # Azimuth 裁切
        crop_g = QGroupBox("Azimuth 裁切显示")
        crop_g.setStyleSheet(_GRP_QSS)
        crop_v = QVBoxLayout(crop_g)

        self.chk_crop = QCheckBox("启用裁切")
        self.chk_crop.setChecked(False)
        self.chk_crop.stateChanged.connect(self._on_crop_changed)
        crop_v.addWidget(self.chk_crop)

        cr1 = QHBoxLayout()
        cr1.addWidget(QLabel("从 (°):"))
        self.spin_crop_min = QDoubleSpinBox()
        self.spin_crop_min.setRange(-720.0, 720.0); self.spin_crop_min.setValue(-10.0)
        self.spin_crop_min.setSingleStep(5.0); self.spin_crop_min.setSuffix(" °")
        self.spin_crop_min.setFixedWidth(90)
        self.spin_crop_min.valueChanged.connect(self._on_crop_changed)
        cr1.addWidget(self.spin_crop_min); cr1.addStretch()
        crop_v.addLayout(cr1)

        cr2 = QHBoxLayout()
        cr2.addWidget(QLabel("到 (°):"))
        self.spin_crop_max = QDoubleSpinBox()
        self.spin_crop_max.setRange(-720.0, 720.0); self.spin_crop_max.setValue(120.0)
        self.spin_crop_max.setSingleStep(5.0); self.spin_crop_max.setSuffix(" °")
        self.spin_crop_max.setFixedWidth(90)
        self.spin_crop_max.valueChanged.connect(self._on_crop_changed)
        cr2.addWidget(self.spin_crop_max); cr2.addStretch()
        crop_v.addLayout(cr2)

        btn_reset_view = QPushButton("⟳ 自动恢复视图范围")
        btn_reset_view.setStyleSheet(_BTN_QSS)
        btn_reset_view.clicked.connect(self.reset_view)
        crop_v.addWidget(btn_reset_view)
        lv.addWidget(crop_g)

        lv.addStretch()

        # ── 右栏（图像） ─────────────────────────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)

        self.fig = Figure(figsize=(7, 6))
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.fig.tight_layout()
        self.canvas.mpl_connect('scroll_event', self._on_scroll)
        rv.addWidget(self.canvas)

        self.status_bar = QStatusBar()
        self.status_bar.setFixedHeight(22)
        self.status_bar.setStyleSheet(
            "background:#ebfaff;color:#103d7e;border-top:1px solid #7096D1;font-size:12px;")
        rv.addWidget(self.status_bar)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([350, 900])

        self._show_placeholder()
        self.spin_crop_min.setEnabled(False)
        self.spin_crop_max.setEnabled(False)

    # ──────────────────────────────────────── 槽 ────────────────────────────
    def _set_status(self, msg: str):
        self.status_bar.showMessage(msg)
        self.status_msg.emit(msg)

    def open_image_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入 2D积分图像", "",
            "2D积分数据 (*.npy *.tif *.tiff);;All Files (*)")
        if not path:
            return
        try:
            if path.lower().endswith('.npy'):
                self.image_data = np.load(path)
            else:
                self.image_data = fabio.open(path).data
            if self.image_data is None or self.image_data.ndim != 2:
                raise ValueError("不是有效的二维数组")

            mn = np.min(self.image_data); mx = np.max(self.image_data)
            p99 = float(np.percentile(self.image_data, 99.9)) if self.image_data.size > 1 else float(mx)
            for w in (self.sld_min, self.sld_max, self.spin_min, self.spin_max):
                w.blockSignals(True); w.setRange(int(mn), int(mx)); w.blockSignals(False)
            self.sld_min.setValue(int(mn));  self.spin_min.setValue(int(mn))
            self.sld_max.setValue(int(p99)); self.spin_max.setValue(int(p99))
            self.contrast_min = int(mn); self.contrast_max = int(p99)

            # 尝试自动加载同目录 processing_info.txt
            info_path = os.path.join(os.path.dirname(path), "processing_info.txt")
            if os.path.exists(info_path):
                self._apply_info_file(info_path, silent=True)

            # [v3.1] 加载新图像时总是强制重置视图
            self.display_main_image(force_reset=True)
            self._set_status(
                f"已加载: {os.path.basename(path)}  "
                f"{self.image_data.shape[1]}×{self.image_data.shape[0]}")
        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"无法加载图像:\n{e}")

    def import_info_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入坐标信息文件", "", "文本文件 (*.txt);;All Files (*)")
        if path:
            self._apply_info_file(path)

    def _apply_info_file(self, path: str, silent: bool = False):
        ranges = InfoFileParser.parse(path)
        if not ranges:
            if not silent:
                QMessageBox.warning(self, "解析失败", f"无法从文件解析坐标范围。\n{path}")
            return
        if 'q_min'       in ranges: self.q_min_edt.setText(str(ranges['q_min']))
        if 'q_max'       in ranges: self.q_max_edt.setText(str(ranges['q_max']))
        if 'azimuth_min' in ranges: self.az_min_edt.setText(str(ranges['azimuth_min']))
        if 'azimuth_max' in ranges: self.az_max_edt.setText(str(ranges['azimuth_max']))
        # [v3.1] force_reset=True：坐标范围改变时必须重置轴限，防止拉伸
        self.update_coordinate_ranges(silent=True, force_reset=True)
        self._set_status(f"坐标范围已从 {os.path.basename(path)} 加载")

    def update_coordinate_ranges(self, silent: bool = False, force_reset: bool = False):
        try:
            qm  = float(self.q_min_edt.text());  qM  = float(self.q_max_edt.text())
            azm = float(self.az_min_edt.text()); azM = float(self.az_max_edt.text())
            if qm >= qM or azm >= azM:
                raise ValueError("Min 必须严格小于 Max")
            self.q_range       = (qm, qM)
            self.azimuth_range = (azm, azM)
            if self.image_data is not None:
                # [v3.1] 坐标范围改变时强制重置，避免旧轴限导致的拉伸/错位
                self.display_main_image(force_reset=True)
        except ValueError as e:
            if not silent:
                QMessageBox.critical(self, "输入错误", f"无效坐标范围:\n{e}")

    def _import_miller_dialog(self, source: str):
        label = "FullMiller" if source == "full" else "outputMiller"
        path, _ = QFileDialog.getOpenFileName(
            self, f"导入 {label}.txt", "", "文本文件 (*.txt);;All Files (*)")
        if not path:
            return
        data = MillerFileParser.parse(path)
        if not data:
            self._set_status(f"错误: 无法从 {os.path.basename(path)} 解析有效数据")
            return
        if source == "full":
            self.full_miller_raw = data
            self.lbl_full_stat.setText(f"FullMiller: {len(data)} 点")
        else:
            self.output_miller_raw = data
            self.lbl_output_stat.setText(f"outputMiller: {len(data)} 点")
        self._remap_miller()
        self.display_main_image()
        self._set_status(f"已导入 {len(data)} 个 {label} 点 ← {os.path.basename(path)}")

    def _remap_miller(self):
        """使用 PsiAzimuthMapper 重新映射所有 Miller 点"""
        self.full_miller_mapped   = self._mapper.map_miller_list(self.full_miller_raw)
        self.output_miller_mapped = self._mapper.map_miller_list(self.output_miller_raw)

    def _on_miller_settings_changed(self):
        self._mapper.convention = self.conv_combo.currentData()
        self._mapper.offset     = self.offset_spin.value()
        self._remap_miller()
        self.display_main_image()

    # ──────────────────────────────────────── 显示 ───────────────────────────
    def _show_placeholder(self):
        self.ax.clear()
        self.ax.text(0.5, 0.5, "请导入 2D积分图像 (.npy / .tif)",
                     ha='center', va='center', transform=self.ax.transAxes,
                     fontsize=14, color='#7096D1')
        self.ax.set_xticks([]); self.ax.set_yticks([])
        self.canvas.draw()

    def display_main_image(self, force_reset: bool = False):
        """
        渲染图像。
        force_reset=True  → 始终将轴限重置为当前坐标范围（推荐在范围变化后调用）
        force_reset=False → 尽量保留当前视图缩放/平移状态
        """
        if self.image_data is None:
            self._show_placeholder()
            return

        cur_xl = self.ax.get_xlim()
        cur_yl = self.ax.get_ylim()
        is_initial = (cur_xl == (0.0, 1.0) and cur_yl == (0.0, 1.0))

        self.ax.clear()
        self.ax.imshow(
            self.image_data,
            aspect='auto',
            origin='lower',
            cmap=ColormapRenderer.mpl_cmap(self.current_colormap),
            vmin=self.contrast_min,
            vmax=self.contrast_max,
            extent=[self.q_range[0],       self.q_range[1],
                    self.azimuth_range[0],  self.azimuth_range[1]],
        )
        self.ax.set_xlabel(r"q ($\AA^{-1}$)", fontsize=11)
        self.ax.set_ylabel("Azimuth (°)", fontsize=11)
        self.ax.set_title("2D积分图像", fontsize=12)

        # Miller 点
        if self.full_miller_mapped:
            qs  = [m['q']  for m in self.full_miller_mapped]
            azs = [m['az'] for m in self.full_miller_mapped]
            self.ax.scatter(qs, azs, s=30, facecolors='none',
                            edgecolors=_MPL_FULL, linewidths=1.5, zorder=10, label="FullMiller")

        if self.output_miller_mapped:
            qs  = [m['q']  for m in self.output_miller_mapped]
            azs = [m['az'] for m in self.output_miller_mapped]
            self.ax.scatter(qs, azs, s=35, marker='D', facecolors='none',
                            edgecolors=_MPL_OUTPUT, linewidths=1.8, zorder=10, label="outputMiller")

        # 图例
        handles = []
        if self.full_miller_mapped:
            handles.append(mpatches.Patch(
                facecolor='none', edgecolor=_MPL_FULL, linewidth=1.5, label="FullMiller"))
        if self.output_miller_mapped:
            handles.append(mpatches.Patch(
                facecolor='none', edgecolor=_MPL_OUTPUT, linewidth=1.8, label="outputMiller"))
        if handles:
            self.ax.legend(handles=handles, loc='upper right', fontsize=9, framealpha=0.7)

        # [v3.1] 轴限设置逻辑：force_reset 或初始状态 → 重置到坐标范围；否则恢复上次视图
        if force_reset or is_initial:
            self.ax.set_xlim(self.q_range)
            if self.az_crop_enabled:
                self.ax.set_ylim(self.az_crop_min, self.az_crop_max)
            else:
                self.ax.set_ylim(self.azimuth_range)
        else:
            self.ax.set_xlim(cur_xl)
            if self.az_crop_enabled:
                self.ax.set_ylim(self.az_crop_min, self.az_crop_max)
            else:
                self.ax.set_ylim(cur_yl)

        self.fig.tight_layout()
        self.canvas.draw()

    def _refresh_full(self):
        """[v3.1] 刷新图像：强制重置视图范围并完整重绘"""
        self.display_main_image(force_reset=True)
        self._set_status("图像已刷新，视图已重置")

    def _mpl_cmap(self):
        return ColormapRenderer.mpl_cmap(self.current_colormap)

    def _on_cmap_changed(self):
        self.current_colormap = self.cmap_combo.currentText()
        if self.image_data is not None:
            self.display_main_image()

    def _on_contrast_changed(self):
        s = self.sender()
        if s is self.sld_min:
            self.spin_min.blockSignals(True); self.spin_min.setValue(self.sld_min.value()); self.spin_min.blockSignals(False)
        elif s is self.spin_min:
            self.sld_min.blockSignals(True);  self.sld_min.setValue(self.spin_min.value());  self.sld_min.blockSignals(False)
        elif s is self.sld_max:
            self.spin_max.blockSignals(True); self.spin_max.setValue(self.sld_max.value()); self.spin_max.blockSignals(False)
        elif s is self.spin_max:
            self.sld_max.blockSignals(True);  self.sld_max.setValue(self.spin_max.value());  self.sld_max.blockSignals(False)
        self.contrast_min = self.spin_min.value()
        self.contrast_max = self.spin_max.value()
        if self.image_data is not None:
            self.display_main_image()

    def _on_scroll(self, event):
        if self.image_data is None or event.xdata is None:
            return
        sf = 1.1 if event.button == 'up' else 1/1.1
        xl = self.ax.get_xlim(); yl = self.ax.get_ylim()
        xd, yd = event.xdata, event.ydata
        self.ax.set_xlim([(xl[0]-xd)*sf+xd, (xl[1]-xd)*sf+xd])
        self.ax.set_ylim([(yl[0]-yd)*sf+yd, (yl[1]-yd)*sf+yd])
        self.canvas.draw()

    def _on_crop_changed(self):
        self.az_crop_enabled = self.chk_crop.isChecked()
        self.az_crop_min     = self.spin_crop_min.value()
        self.az_crop_max     = self.spin_crop_max.value()
        self.spin_crop_min.setEnabled(self.az_crop_enabled)
        self.spin_crop_max.setEnabled(self.az_crop_enabled)
        if self.image_data is not None:
            self.display_main_image()

    def reset_view(self):
        """恢复图像到完整坐标范围（或裁切范围）"""
        if self.image_data is None:
            return
        self.ax.set_xlim(self.q_range)
        if self.az_crop_enabled:
            self.ax.set_ylim(self.az_crop_min, self.az_crop_max)
        else:
            self.ax.set_ylim(self.azimuth_range)
        self.canvas.draw()
        self._set_status("视图已恢复")

    def clear_all_miller(self):
        self.full_miller_raw = [];  self.output_miller_raw  = []
        self.full_miller_mapped = []; self.output_miller_mapped = []
        self.lbl_full_stat.setText("FullMiller: 未加载")
        self.lbl_output_stat.setText("outputMiller: 未加载")
        self.display_main_image()
        self._set_status("已清除所有 Miller 标记")

    def save_marked_image(self):
        if self.image_data is None:
            self._set_status("错误: 请先加载图像")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存标记图像", "", "PNG (*.png);;All Files (*)")
        if not path:
            return
        try:
            self.fig.savefig(path, dpi=200, bbox_inches='tight')
            self._set_status(f"已保存: {path}")
        except Exception as e:
            self._set_status(f"保存失败: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 来源选择栏
# ═══════════════════════════════════════════════════════════════════════════

class SourceSelectBar(QWidget):
    """顶部数据来源选择条"""
    # PySide6 使用 Signal 替换 pyqtSignal
    source_changed = Signal(int)   # 0 = Raw, 1 = 2D Integrated

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("source_bar")
        self.setFixedHeight(52)
        self.setStyleSheet(_SOURCE_BAR_QSS)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 6, 16, 6)

        lbl = QLabel("数据来源：")
        lbl.setObjectName("src_title")
        lay.addWidget(lbl)

        self.btn_group = QButtonGroup(self)
        self.rb_raw = QRadioButton("原始衍射图  (.tif / .edf / .cbf)")
        self.rb_2d  = QRadioButton("2D 积分图像  (.npy / .tif)")
        self.rb_raw.setChecked(True)
        for rb in (self.rb_raw, self.rb_2d):
            self.btn_group.addButton(rb)
            lay.addWidget(rb)

        lay.addStretch()

        self.rb_raw.toggled.connect(
            lambda checked: self.source_changed.emit(0) if checked else None)
        self.rb_2d.toggled.connect(
            lambda checked: self.source_changed.emit(1) if checked else None)


# ═══════════════════════════════════════════════════════════════════════════
# 主窗口
# ═══════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("后处理查看器 v3.1 — 选择数据来源后开始工作")
        self.setGeometry(0, 0, 1600, 950)
        self.showMaximized()
        self.setStyleSheet("QMainWindow{background:#edf2ff;}")

        central = QWidget()
        cv = QVBoxLayout(central)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)

        self.src_bar = SourceSelectBar()
        self.src_bar.source_changed.connect(self._on_source_changed)
        cv.addWidget(self.src_bar)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#7ad6fb;"); sep.setFixedHeight(2)
        cv.addWidget(sep)

        self.stack = QStackedWidget()
        self.raw_panel = RawImagePanel()
        self.int_panel = Integrated2DSimplePanel()
        self.stack.addWidget(self.raw_panel)
        self.stack.addWidget(self.int_panel)
        cv.addWidget(self.stack)

        self.setCentralWidget(central)

        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet(
            "background:#ebfaff;color:#103d7e;border-top:1px solid #7096D1;font-size:12px;")
        self.raw_panel.status_msg.connect(self.status_bar.showMessage)
        self.int_panel.status_msg.connect(self.status_bar.showMessage)

        self._build_menus()
        self._on_source_changed(0)

    # ──────────────────────────────────────── 菜单 ───────────────────────────
    def _build_menus(self):
        mb = self.menuBar()
        fm = mb.addMenu("文件(&F)")

        self.act_open_raw = QAction("打开衍射图像…", self)
        self.act_open_raw.triggered.connect(self.raw_panel.open_image_file)
        fm.addAction(self.act_open_raw)

        self.act_open_poni = QAction("导入 PONI 文件…", self)
        self.act_open_poni.triggered.connect(self.raw_panel.import_poni_file)
        fm.addAction(self.act_open_poni)

        self.act_full_raw = QAction("导入 FullMiller.txt  (原始衍射图)…", self)
        self.act_full_raw.triggered.connect(
            lambda: self.raw_panel._import_miller_dialog("full"))
        fm.addAction(self.act_full_raw)

        self.act_output_raw = QAction("导入 outputMiller.txt  (原始衍射图)…", self)
        self.act_output_raw.triggered.connect(
            lambda: self.raw_panel._import_miller_dialog("output"))
        fm.addAction(self.act_output_raw)

        self.act_save_raw = QAction("保存标记图像  (原始衍射图)…", self)
        self.act_save_raw.triggered.connect(self.raw_panel.save_marked_image)
        fm.addAction(self.act_save_raw)

        fm.addSeparator()

        self.act_open_2d = QAction("打开 2D积分图像 (.npy/.tif)…", self)
        self.act_open_2d.triggered.connect(self.int_panel.open_image_file)
        fm.addAction(self.act_open_2d)

        self.act_import_info = QAction("导入坐标信息文件 (.txt)…", self)
        self.act_import_info.triggered.connect(self.int_panel.import_info_file)
        fm.addAction(self.act_import_info)

        self.act_full_2d = QAction("导入 FullMiller.txt  (2D积分图)…", self)
        self.act_full_2d.triggered.connect(
            lambda: self.int_panel._import_miller_dialog("full"))
        fm.addAction(self.act_full_2d)

        self.act_output_2d = QAction("导入 outputMiller.txt  (2D积分图)…", self)
        self.act_output_2d.triggered.connect(
            lambda: self.int_panel._import_miller_dialog("output"))
        fm.addAction(self.act_output_2d)

        self.act_save_2d = QAction("保存标记图像  (2D积分图)…", self)
        self.act_save_2d.triggered.connect(self.int_panel.save_marked_image)
        fm.addAction(self.act_save_2d)

        fm.addSeparator()
        quit_act = QAction("退出", self)
        quit_act.triggered.connect(self.close)
        fm.addAction(quit_act)

        hm = mb.addMenu("帮助(&H)")
        about_act = QAction("关于", self)
        about_act.triggered.connect(self._show_about)
        hm.addAction(about_act)

    def _on_source_changed(self, idx: int):
        self.stack.setCurrentIndex(idx)
        is_raw = (idx == 0)
        raw_acts = (self.act_open_raw, self.act_open_poni,
                    self.act_full_raw, self.act_output_raw, self.act_save_raw)
        int_acts = (self.act_open_2d, self.act_import_info,
                    self.act_full_2d, self.act_output_2d, self.act_save_2d)
        for a in raw_acts: a.setVisible(is_raw)
        for a in int_acts: a.setVisible(not is_raw)
        title = "原始衍射图模式" if is_raw else "2D积分图像模式"
        self.setWindowTitle(f"后处理查看器 v3.1 — {title}")
        self.status_bar.showMessage(f"当前模式: {title}")

    def _show_about(self):
        pyfai_info = "pyFAI InvertGeometry ✓" if PYFAI_OK else "pyFAI 未安装 (使用手动计算)"
        QMessageBox.information(self, "关于", (
            "后处理查看器 v3.1  [PySide6 版]\n\n"
            "【v3.1 改进】\n"
            "  · 原始衍射图：新增「刷新视图」按钮，防止显示异常累积\n"
            "  · ψ 旋转偏移：修正 Q2/Q4 象限方向错误，统一以 Q1 为基准\n"
            "  · 原始衍射图：图像加载后自动居中\n"
            "  · 2D积分图：导入坐标信息后强制重置轴限，修复拉伸\n"
            "  · 2D积分图：新增「刷新图像」按钮\n"
            "  · 代码结构：核心功能抽离至 diffraction_utils.py\n\n"
            "【来源 A】原始衍射图  (.tif / .edf / .cbf)\n"
            "  · pyFAI InvertGeometry 精确映射 (q, ψ) → 像素\n"
            "  · 无 PONI 时用手动参数近似计算\n"
            "  · FullMiller → 青色方块  outputMiller → 橙色菱形\n\n"
            "【来源 B】2D 积分图像  (.npy / .tif)\n"
            "  · 直接将 (q, ψ) 按坐标范围映射到图像坐标\n"
            "  · 可自动读取 processing_info.txt 中的坐标范围\n"
            "  · FullMiller → 青色空心圆  outputMiller → 橙色空心菱形\n\n"
            f"pyFAI 状态: {pyfai_info}"
        ))


# ═══════════════════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
