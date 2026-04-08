"""
integrated_tab.py  –  2D 积分图像寻峰选项卡.

Loads pre-processed 2D integration maps (q × azimuth, .npy or .tif),
generates 1D slices, runs peak-finding, and lets the user record peaks.
Supports Miller-index overlay and quick view cropping.
"""

from __future__ import annotations

import csv
import os
import re
import traceback

import fabio
import matplotlib.patches as patches
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.signal import find_peaks

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QRadioButton, QScrollArea, QSlider,
    QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from .image_processor import ImageProcessor
from .styles import AppStyles
from .utils import normalize_angle_to_180, parse_info_file


class IntegratedTab(QWidget):
    """Widget for 2D integrated data peak picking (积分图像提取点).

    Embed this widget inside a ``QTabWidget`` in the main window.
    The *status_bar* parameter should be the ``QMainWindow.statusBar()``
    instance so this tab can post messages to the shared status bar.
    """

    def __init__(self, status_bar, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._status_bar = status_bar

        # ── data ────────────────────────────────────────────────────────
        self.image_data: np.ndarray | None = None
        self.q_range: tuple[float, float] = (0.0, 1.0)
        self.azimuth_range: tuple[float, float] = (-180.0, 180.0)

        # ── display ──────────────────────────────────────────────────────
        self.contrast_min: float = 0
        self.contrast_max: float = 65535
        self.current_colormap: str = "灰度"

        # ── selection state ──────────────────────────────────────────────
        self.selection_mode: str = "精准"
        self.current_selection_patch = None
        self.rough_selection_start_pos: tuple | None = None
        self.slice_center_q: float | None = None
        self.slice_center_azimuth: float | None = None
        self.selected_q_peak_value: float | None = None
        self.selected_azimuth_peak_value: float | None = None
        self.found_q_peaks_list: list[dict] = []
        self.found_azimuth_peaks_list: list[dict] = []
        self.rough_selection_q_range: tuple | None = None
        self.rough_selection_azimuth_range: tuple | None = None

        # ── records ──────────────────────────────────────────────────────
        self.recorded_peaks: list[dict] = []

        # ── Miller indices ────────────────────────────────────────────────
        self.miller_indices_data: list[dict] = []
        self._original_miller_indices_data: list[dict] = []
        self.show_miller_indices: bool = False
        self.miller_index_annotations: list = []
        self.psi_convention_mode: str = "0_horizontal_ccw"
        self.miller_0_azimuth_ref: float = 0.0

        self._build_ui()

    # ================================================================== #
    #  UI construction                                                     #
    # ================================================================== #

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(AppStyles.SPLITTER)
        root.addWidget(splitter)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([1000, 600])

    # ── Left panel ─────────────────────────────────────────────────────

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(5, 5, 5, 5)

        # Main matplotlib canvas
        img_grp = QGroupBox("2D 积分图像")
        img_grp.setStyleSheet(AppStyles.IMAGE_GROUP)
        img_lay = QVBoxLayout(img_grp)

        self.main_figure = Figure(figsize=(5, 5))
        self.main_canvas = FigureCanvas(self.main_figure)
        self.main_ax = self.main_figure.add_subplot(111)
        self.main_figure.tight_layout()

        self.main_canvas.mpl_connect("button_press_event",   self._main_mouse_press)
        self.main_canvas.mpl_connect("motion_notify_event",  self._main_mouse_move)
        self.main_canvas.mpl_connect("button_release_event", self._main_mouse_release)
        self.main_canvas.mpl_connect("scroll_event",         self._main_scroll)

        img_lay.addWidget(self.main_canvas)
        lay.addWidget(img_grp, 4)

        # Settings scroll area
        settings_grp = QGroupBox("显示与坐标设置")
        settings_grp.setStyleSheet(AppStyles.GROUP)
        settings_lay = QVBoxLayout(settings_grp)

        # Coordinate ranges
        coord_grp = QGroupBox("坐标范围")
        coord_grp.setStyleSheet(AppStyles.GROUP)
        coord_form = QFormLayout(coord_grp)
        self.q_min_edit      = QLineEdit("0.0")
        self.q_max_edit      = QLineEdit("1.0")
        self.azimuth_min_edit = QLineEdit("-180.0")
        self.azimuth_max_edit = QLineEdit("180.0")
        apply_ranges_btn = QPushButton("应用/更新坐标范围")
        apply_ranges_btn.setStyleSheet(AppStyles.BUTTON)
        apply_ranges_btn.clicked.connect(self._update_coordinate_ranges)
        coord_form.addRow("q Min:", self.q_min_edit)
        coord_form.addRow("q Max:", self.q_max_edit)
        coord_form.addRow("方位角 Min (°):", self.azimuth_min_edit)
        coord_form.addRow("方位角 Max (°):", self.azimuth_max_edit)
        coord_form.addRow(apply_ranges_btn)
        settings_lay.addWidget(coord_grp)

        # Quick view crop
        qv_grp = QGroupBox("快速视图裁剪 (基于米勒设定)")
        qv_grp.setStyleSheet(AppStyles.GROUP)
        qv_form = QFormLayout(qv_grp)
        info_lbl = QLabel("范围: Miller −30° 至 +120°\n基准: 使用下方米勒设置")
        info_lbl.setStyleSheet("color:#103d7e; font: italic 10pt 'Microsoft Yahei';")
        qv_form.addRow(info_lbl)
        qv_btns = QHBoxLayout()
        crop_btn = QPushButton("裁剪视图 (−30 ~ 120°)")
        crop_btn.setStyleSheet(AppStyles.BUTTON)
        crop_btn.clicked.connect(self._apply_quick_azimuth_range)
        restore_btn = QPushButton("恢复全视图")
        restore_btn.setStyleSheet(AppStyles.BUTTON)
        restore_btn.clicked.connect(self._restore_full_view)
        qv_btns.addWidget(crop_btn)
        qv_btns.addWidget(restore_btn)
        qv_form.addRow(qv_btns)
        settings_lay.addWidget(qv_grp)

        # Contrast
        ct_grp = QGroupBox("对比度调节")
        ct_grp.setStyleSheet(AppStyles.GROUP)
        ct_lay = QVBoxLayout(ct_grp)
        self.min_slider = QSlider(Qt.Orientation.Horizontal)
        self.min_slider.setRange(0, 65535)
        self.min_slider.valueChanged.connect(self._update_contrast)
        self.max_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_slider.setRange(0, 65535)
        self.max_slider.setValue(65535)
        self.max_slider.valueChanged.connect(self._update_contrast)
        self.min_value_label = QLabel("Min: 0")
        self.max_value_label = QLabel("Max: 65535")
        ct_lay.addWidget(self.min_value_label)
        ct_lay.addWidget(self.min_slider)
        ct_lay.addWidget(self.max_value_label)
        ct_lay.addWidget(self.max_slider)
        settings_lay.addWidget(ct_grp)

        # Colormap + Miller indices
        cmap_grp = QGroupBox("图像显示设置")
        cmap_grp.setStyleSheet(AppStyles.GROUP)
        cmap_form = QFormLayout(cmap_grp)
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(["灰度", "反转灰度", "热力图", "彩虹"])
        self.colormap_combo.currentIndexChanged.connect(self._update_colormap)
        cmap_form.addRow("颜色映射:", self.colormap_combo)

        self.miller_indices_checkbox = QCheckBox("显示米勒指数点")
        self.miller_indices_checkbox.setChecked(False)
        self.miller_indices_checkbox.toggled.connect(self._toggle_miller_display)
        cmap_form.addRow(self.miller_indices_checkbox)

        # Miller settings sub-group
        miller_sub = QGroupBox("米勒指数映射设置")
        miller_sub.setStyleSheet(AppStyles.GROUP.replace("font-size: 18px", "font-size: 14px"))
        miller_form = QFormLayout(miller_sub)

        self.miller_psi_convention_combo = QComboBox()
        self.miller_psi_convention_combo.addItem("图像 Azimuth 与标准 CCW 一致",  "0_horizontal_cw")
        self.miller_psi_convention_combo.addItem("图像 Azimuth 与标准 CCW 相反", "0_horizontal_ccw")
        self.miller_psi_convention_combo.setCurrentIndex(1)
        self.miller_psi_convention_combo.currentIndexChanged.connect(self._update_miller_settings)
        miller_form.addRow("图像 Azimuth 约定:", self.miller_psi_convention_combo)

        self.miller_0_azimuth_spin = QDoubleSpinBox()
        self.miller_0_azimuth_spin.setSuffix(" °")
        self.miller_0_azimuth_spin.setDecimals(2)
        self.miller_0_azimuth_spin.setRange(-360.0, 360.0)
        self.miller_0_azimuth_spin.setSingleStep(1.0)
        self.miller_0_azimuth_spin.valueChanged.connect(self._update_miller_settings)
        miller_form.addRow("Miller 0° 对应图像 Azimuth:", self.miller_0_azimuth_spin)
        cmap_form.addWidget(miller_sub)
        settings_lay.addWidget(cmap_grp)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(settings_grp)
        lay.addWidget(scroll, 1)
        return w

    # ── Right panel ────────────────────────────────────────────────────

    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(5, 5, 5, 5)

        tabs = QTabWidget()
        tabs.setStyleSheet(AppStyles.TAB_WIDGET)
        lay.addWidget(tabs)

        tabs.addTab(self._build_tab_analysis(), "分析与寻峰")
        tabs.addTab(self._build_tab_records(),  "寻峰记录")
        return w

    # ── Tab 0: Analysis ────────────────────────────────────────────────

    def _build_tab_analysis(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)

        # File import
        file_grp = QGroupBox("导入数据")
        file_grp.setStyleSheet(AppStyles.GROUP)
        file_lay = QVBoxLayout(file_grp)
        file_btns = QHBoxLayout()

        open_btn = QPushButton("打开 2D 积分数据 (npy/tif)")
        open_btn.setStyleSheet(AppStyles.BUTTON)
        open_btn.clicked.connect(self.open_file)
        file_btns.addWidget(open_btn)

        info_btn = QPushButton("导入坐标信息文件 (txt)")
        info_btn.setStyleSheet(AppStyles.BUTTON)
        info_btn.clicked.connect(self._import_info_file_manually)
        file_btns.addWidget(info_btn)

        miller_btn = QPushButton("导入米勒指数文件")
        miller_btn.setStyleSheet(AppStyles.BUTTON)
        miller_btn.clicked.connect(self.import_miller_indices_file)
        file_btns.addWidget(miller_btn)
        file_lay.addLayout(file_btns)
        lay.addWidget(file_grp)

        # 1D Slice plots
        slice_grp = QGroupBox("1D 切片图")
        slice_grp.setStyleSheet(AppStyles.GROUP)
        slice_lay = QVBoxLayout(slice_grp)

        self.q_slice_figure   = Figure(figsize=(5, 3))
        self.q_slice_canvas   = FigureCanvas(self.q_slice_figure)
        self.q_slice_ax       = self.q_slice_figure.add_subplot(111)
        self.q_slice_figure.tight_layout()

        self.az_slice_figure  = Figure(figsize=(5, 3))
        self.az_slice_canvas  = FigureCanvas(self.az_slice_figure)
        self.az_slice_ax      = self.az_slice_figure.add_subplot(111)
        self.az_slice_figure.tight_layout()

        self.q_slice_canvas.mpl_connect("button_press_event", self._on_q_slice_click)
        self.az_slice_canvas.mpl_connect("button_press_event", self._on_az_slice_click)

        slice_lay.addWidget(self.q_slice_canvas)
        slice_lay.addWidget(self.az_slice_canvas)
        lay.addWidget(slice_grp)

        # Selection / peak-finding tools
        sel_grp = QGroupBox("选择与寻峰工具")
        sel_grp.setStyleSheet(AppStyles.GROUP)
        sel_lay = QVBoxLayout(sel_grp)

        mode_row = QHBoxLayout()
        self.precise_radio = QRadioButton("精准选择 (点击主图定切片，点击切片选峰)")
        self.rough_radio   = QRadioButton("粗略选择 (拖拽主图定区域，寻峰)")
        self.precise_radio.setChecked(True)
        self.precise_radio.toggled.connect(self._update_selection_mode)
        mode_row.addWidget(self.precise_radio)
        mode_row.addWidget(self.rough_radio)
        sel_lay.addLayout(mode_row)

        # Slice width / range parameters
        params_row = QHBoxLayout()

        q_slice_sub = QGroupBox("横向切片设置 (q-slice)")
        q_slice_sub.setStyleSheet(AppStyles.GROUP.replace("font-size: 18px", "font-size: 14px"))
        q_slice_form = QFormLayout(q_slice_sub)
        self.q_slice_int_width_spin = QDoubleSpinBox()
        self.q_slice_int_width_spin.setSuffix(" °"); self.q_slice_int_width_spin.setDecimals(1)
        self.q_slice_int_width_spin.setRange(0.1, 180.0); self.q_slice_int_width_spin.setValue(1.0)
        self.q_slice_int_width_spin.setSingleStep(0.5)
        self.q_slice_int_width_spin.valueChanged.connect(self._update_slice_plots)
        q_slice_form.addRow("积分宽度 (Azimuth):", self.q_slice_int_width_spin)

        self.q_slice_disp_range_spin = QDoubleSpinBox()
        self.q_slice_disp_range_spin.setSuffix(" (q)"); self.q_slice_disp_range_spin.setDecimals(3)
        self.q_slice_disp_range_spin.setRange(0.001, 10.0); self.q_slice_disp_range_spin.setValue(0.2)
        self.q_slice_disp_range_spin.setSingleStep(0.05)
        self.q_slice_disp_range_spin.valueChanged.connect(self._update_slice_plots)
        q_slice_form.addRow("显示范围 (q):", self.q_slice_disp_range_spin)
        params_row.addWidget(q_slice_sub)

        az_slice_sub = QGroupBox("纵向切片设置 (Azimuth-slice)")
        az_slice_sub.setStyleSheet(AppStyles.GROUP.replace("font-size: 18px", "font-size: 14px"))
        az_slice_form = QFormLayout(az_slice_sub)
        self.az_slice_int_width_spin = QDoubleSpinBox()
        self.az_slice_int_width_spin.setSuffix(" (q)"); self.az_slice_int_width_spin.setDecimals(3)
        self.az_slice_int_width_spin.setRange(0.001, 10.0); self.az_slice_int_width_spin.setValue(0.01)
        self.az_slice_int_width_spin.setSingleStep(0.005)
        self.az_slice_int_width_spin.valueChanged.connect(self._update_slice_plots)
        az_slice_form.addRow("积分宽度 (q):", self.az_slice_int_width_spin)

        self.az_slice_disp_range_spin = QDoubleSpinBox()
        self.az_slice_disp_range_spin.setSuffix(" °"); self.az_slice_disp_range_spin.setDecimals(1)
        self.az_slice_disp_range_spin.setRange(1.0, 360.0); self.az_slice_disp_range_spin.setValue(20.0)
        self.az_slice_disp_range_spin.setSingleStep(5.0)
        self.az_slice_disp_range_spin.valueChanged.connect(self._update_slice_plots)
        az_slice_form.addRow("显示范围 (Azimuth):", self.az_slice_disp_range_spin)
        params_row.addWidget(az_slice_sub)
        sel_lay.addLayout(params_row)

        # Peak-finding parameters (粗略模式)
        self.peak_finding_grp = QGroupBox("寻峰参数")
        self.peak_finding_grp.setStyleSheet(AppStyles.GROUP.replace("font-size: 18px", "font-size: 14px"))
        pf_form = QFormLayout(self.peak_finding_grp)
        self.peak_prominence_spin = QDoubleSpinBox()
        self.peak_prominence_spin.setRange(0.0, 1_000_000.0)
        self.peak_prominence_spin.setValue(100.0); self.peak_prominence_spin.setSingleStep(10.0)
        pf_form.addRow("峰值突出度 (Prominence):", self.peak_prominence_spin)
        self.peak_width_spin = QDoubleSpinBox()
        self.peak_width_spin.setRange(0.0, 1000.0)
        self.peak_width_spin.setValue(1.0); self.peak_width_spin.setSingleStep(0.1)
        pf_form.addRow("峰值宽度 (Width):", self.peak_width_spin)
        sel_lay.addWidget(self.peak_finding_grp)

        self.selection_info_label = QLabel("当前选择: 无")
        self.selection_info_label.setWordWrap(True)
        sel_lay.addWidget(self.selection_info_label)

        act_row = QHBoxLayout()
        self.find_peaks_btn = QPushButton("在切片图中寻峰")
        self.find_peaks_btn.setStyleSheet(AppStyles.BUTTON)
        self.find_peaks_btn.clicked.connect(self._find_peaks_in_slices)
        self.record_peaks_btn = QPushButton("记录寻得的峰")
        self.record_peaks_btn.setStyleSheet(AppStyles.BUTTON)
        self.record_peaks_btn.clicked.connect(self._record_found_peaks)
        self.clear_sel_btn = QPushButton("清除当前选择")
        self.clear_sel_btn.setStyleSheet(AppStyles.BUTTON)
        self.clear_sel_btn.clicked.connect(self._clear_current_selection)
        act_row.addWidget(self.find_peaks_btn)
        act_row.addWidget(self.record_peaks_btn)
        act_row.addWidget(self.clear_sel_btn)
        sel_lay.addLayout(act_row)
        lay.addWidget(sel_grp)

        self._update_selection_mode()
        return tab

    # ── Tab 1: Records ─────────────────────────────────────────────────

    def _build_tab_records(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)

        self.record_list = QListWidget()
        lay.addWidget(self.record_list)

        act_row = QHBoxLayout()
        del_btn = QPushButton("删除选中记录")
        del_btn.setStyleSheet(AppStyles.BUTTON)
        del_btn.clicked.connect(self._delete_selected_record)
        clear_btn = QPushButton("删除所有记录")
        clear_btn.setStyleSheet(AppStyles.BUTTON)
        clear_btn.clicked.connect(self._clear_all_records)
        export_btn = QPushButton("导出记录为 CSV 和图像")
        export_btn.setStyleSheet(AppStyles.BUTTON)
        export_btn.clicked.connect(self.export_recorded_peaks)
        act_row.addWidget(del_btn)
        act_row.addWidget(clear_btn)
        act_row.addWidget(export_btn)
        lay.addLayout(act_row)
        return tab

    # ── Helpers ────────────────────────────────────────────────────────

    def _show_status(self, msg: str) -> None:
        self._status_bar.showMessage(msg)

    # ================================================================== #
    #  File I/O                                                            #
    # ================================================================== #

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "打开 2D 积分图像", "",
            "2D 积分数据 (*.npy *.tiff *.tif);;所有文件 (*.*)"
        )
        if not path:
            return
        try:
            if path.lower().endswith((".tif", ".tiff")):
                self.image_data = fabio.open(path).data
            elif path.lower().endswith(".npy"):
                self.image_data = np.load(path)
            else:
                raise ValueError("不支持的文件格式")

            info_path = os.path.join(os.path.dirname(path), "processing_info.txt")
            if os.path.exists(info_path):
                self._load_info_from_file(info_path)
            else:
                self._show_status(
                    f"已加载: {os.path.basename(path)}。"
                    "未找到 processing_info.txt，请手动设置坐标范围。"
                )

            if self.image_data is not None and self.image_data.size > 0:
                lo  = int(np.min(self.image_data))
                hi  = int(np.max(self.image_data))
                p99 = int(np.percentile(self.image_data, 99.9)) if self.image_data.size > 1 else hi
                self.min_slider.setRange(lo, hi); self.max_slider.setRange(lo, hi)
                self.min_slider.setValue(lo);     self.max_slider.setValue(p99)
                self.contrast_min = lo;           self.contrast_max = p99
                self.min_value_label.setText(f"Min: {lo}")
                self.max_value_label.setText(f"Max: {p99}")

            if self.q_range[0] < self.q_range[1] and self.azimuth_range[0] < self.azimuth_range[1]:
                self._display_main_image()
            else:
                QMessageBox.warning(self, "警告", "请设置有效的 q 和方位角坐标范围。")

            self._clear_current_selection()
        except Exception as exc:
            QMessageBox.critical(self, "加载错误", f"无法加载图像:\n{exc}")
            self.image_data = None
            self.main_ax.clear(); self.main_canvas.draw()

    def _import_info_file_manually(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "打开坐标信息文件", "", "文本文件 (*.txt)"
        )
        if path:
            self._load_info_from_file(path)

    def _load_info_from_file(self, file_path: str) -> None:
        ranges = parse_info_file(file_path)
        if not ranges:
            QMessageBox.warning(self, "解析失败", f"无法从 {file_path} 解析坐标范围。")
            return
        if "q_min" in ranges:      self.q_min_edit.setText(str(ranges["q_min"]))
        if "q_max" in ranges:      self.q_max_edit.setText(str(ranges["q_max"]))
        if "azimuth_min" in ranges: self.azimuth_min_edit.setText(str(ranges["azimuth_min"]))
        if "azimuth_max" in ranges: self.azimuth_max_edit.setText(str(ranges["azimuth_max"]))
        all_present = all(k in ranges for k in ("q_min", "q_max", "azimuth_min", "azimuth_max"))
        if all_present:
            self._update_coordinate_ranges()
            self._show_status(f"已从 {os.path.basename(file_path)} 加载并应用坐标范围。")
        else:
            QMessageBox.warning(self, "信息不完整",
                f"从 {os.path.basename(file_path)} 加载的信息不完整，请手动补全。")

    def import_miller_indices_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "导入米勒指数", "",
            "文本文件 (*.txt);;CSV 文件 (*.csv);;所有文件 (*.*)"
        )
        if not path:
            return
        try:
            new_transformed: list[dict] = []
            new_original: list[dict]    = []

            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
            if not lines:
                raise ValueError("文件为空。")

            header_parts = [p.strip() for p in re.split(r"\s+", lines[0].strip()) if p.strip()]
            q_col = az_col = h_col = k_col = l_col = -1
            for i, name in enumerate(header_parts):
                n = name.lower()
                if "q(" in n or n == "q" or "q_value" in n:  q_col = i
                elif "psi(" in n or "azimuth" in n or "chi" in n: az_col = i
                elif n == "h": h_col = i
                elif n == "k": k_col = i
                elif n == "l": l_col = i

            if q_col == -1 or az_col == -1:
                missing = [c for c, v in (("'q'", q_col), ("'azimuth'", az_col)) if v == -1]
                raise ValueError(f"文件缺少 {', '.join(missing)} 列。")

            for row_num, line in enumerate(lines[1:], start=2):
                parts = [p.strip() for p in re.split(r"\s+", line.strip()) if p.strip()]
                if not parts:
                    continue
                try:
                    q_val   = float(parts[q_col])
                    psi_val = float(parts[az_col])
                    h_lbl = int(float(parts[h_col])) if 0 <= h_col < len(parts) else "?"
                    k_lbl = int(float(parts[k_col])) if 0 <= k_col < len(parts) else "?"
                    l_lbl = int(float(parts[l_col])) if 0 <= l_col < len(parts) else "?"
                    hkl = f"({h_lbl} {k_lbl} {l_lbl})"

                    if np.isnan(q_val) or np.isnan(psi_val) or q_val <= 0:
                        continue
                    new_original.append({"q": q_val, "original_psi": psi_val, "hkl": hkl})
                    az_val = self._miller_azimuth_in_image(psi_val)
                    new_transformed.append({"q": q_val, "azimuth": az_val, "hkl": hkl,
                                            "original_psi": psi_val})
                except (ValueError, IndexError):
                    continue

            if new_transformed:
                self._original_miller_indices_data = new_original
                self.miller_indices_data = new_transformed
                self.show_miller_indices = True
                self.miller_indices_checkbox.setChecked(True)
                self._display_main_image()
                self._show_status(
                    f"已成功从 '{os.path.basename(path)}' 导入 {len(new_transformed)} 个米勒指数点。"
                )
            else:
                QMessageBox.warning(self, "导入失败", "文件未包含有效的米勒指数数据。")
        except Exception as exc:
            QMessageBox.critical(self, "导入错误", f"导入米勒指数文件时出错:\n{exc}")

    def export_recorded_peaks(self) -> None:
        if not self.recorded_peaks:
            QMessageBox.warning(self, "无数据", "没有可导出的峰记录。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出寻峰记录", "",
            "CSV 文件 (*.csv);;所有文件 (*.*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not path:
            return
        base = os.path.splitext(path)[0]
        try:
            csv_path = base + ".csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["peak_index", "q_value", "azimuth_value", "intensity"])
                for i, pk in enumerate(self.recorded_peaks):
                    writer.writerow(
                        [i + 1, f"{pk['q']:.6f}", f"{pk['azimuth']:.6f}", f"{pk['intensity']:.6f}"]
                    )
            img_path = base + "_marked_peaks.png"
            self._create_marked_image(img_path)
            self._show_status(f"记录已导出到 {csv_path} 和 {img_path}")
            QMessageBox.information(self, "导出成功",
                f"寻峰记录和图像已成功导出。\nCSV: {csv_path}\n图像: {img_path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", f"导出时出错:\n{exc}")

    # ================================================================== #
    #  Coordinate helpers                                                  #
    # ================================================================== #

    def _update_coordinate_ranges(self) -> None:
        if self.image_data is None:
            QMessageBox.warning(self, "警告", "请先加载 2D 积分图像。")
            return
        try:
            q_min  = float(self.q_min_edit.text())
            q_max  = float(self.q_max_edit.text())
            az_min = float(self.azimuth_min_edit.text())
            az_max = float(self.azimuth_max_edit.text())
            if q_min >= q_max or az_min >= az_max:
                raise ValueError("Min 值必须严格小于 Max 值。")
            self.q_range      = (q_min,  q_max)
            self.azimuth_range = (az_min, az_max)
            self.main_ax.set_xlim(self.q_range)
            self.main_ax.set_ylim(self.azimuth_range)
            self._display_main_image()
            self._clear_current_selection()
            self._show_status(
                f"坐标范围已更新: q [{q_min:.4f}, {q_max:.4f}], "
                f"Azimuth [{az_min:.2f}, {az_max:.2f}]°"
            )
        except ValueError as exc:
            QMessageBox.critical(self, "输入错误", f"无效的坐标范围:\n{exc}")

    def _pixel_to_coords(self, px: float, py: float) -> tuple[float, float]:
        if self.image_data is None:
            return 0.0, 0.0
        rows, cols = self.image_data.shape
        px = np.clip(px, 0, cols - 1)
        py = np.clip(py, 0, rows - 1)
        q  = self.q_range[0] + (px / (cols - 1)) * (self.q_range[1] - self.q_range[0])
        az = self.azimuth_range[0] + (py / (rows - 1)) * (self.azimuth_range[1] - self.azimuth_range[0])
        return q, az

    def _coords_to_pixel(self, q: float, azimuth: float) -> tuple[float, float]:
        if self.image_data is None:
            return 0.0, 0.0
        rows, cols = self.image_data.shape
        q  = np.clip(q, self.q_range[0], self.q_range[1])
        az = np.clip(azimuth, self.azimuth_range[0], self.azimuth_range[1])
        px = (cols - 1) * (q  - self.q_range[0])      / (self.q_range[1] - self.q_range[0])
        py = (rows - 1) * (az - self.azimuth_range[0]) / (self.azimuth_range[1] - self.azimuth_range[0])
        return px, py

    # ================================================================== #
    #  Main image display                                                  #
    # ================================================================== #

    def _display_main_image(self) -> None:
        if self.image_data is None:
            self.main_ax.clear()
            self.main_ax.text(0.5, 0.5, "请加载 .npy 或 .tif 图像文件",
                ha="center", va="center", transform=self.main_ax.transAxes,
                fontsize=14, color="gray")
            self.main_ax.set_xticks([]); self.main_ax.set_yticks([])
            self.main_canvas.draw()
            return

        xlim = self.main_ax.get_xlim()
        ylim = self.main_ax.get_ylim()
        is_default = (xlim == (0.0, 1.0) and ylim == (0.0, 1.0))

        self.main_ax.clear()
        for ann in self.miller_index_annotations:
            pass  # cleared by ax.clear()
        self.miller_index_annotations.clear()

        self.main_ax.imshow(
            self.image_data, aspect="auto", origin="lower",
            cmap=ImageProcessor.matplotlib_cmap(self.current_colormap),
            vmin=self.contrast_min, vmax=self.contrast_max,
            extent=[self.q_range[0], self.q_range[1],
                    self.azimuth_range[0], self.azimuth_range[1]],
        )
        self.main_ax.set_xlabel(r"q ($\AA^{-1}$)")
        self.main_ax.set_ylabel("Azimuth (°)")
        self.main_ax.set_title("2D 积分图像")

        daz = self.azimuth_range[1] - self.azimuth_range[0]
        for i, pk in enumerate(self.recorded_peaks):
            self.main_ax.plot(pk["q"], pk["azimuth"], "x",
                              color="red", markersize=8, mew=2, alpha=0.8, zorder=10)
            self.main_ax.text(pk["q"], pk["azimuth"] + daz * 0.02,
                              f"P{i+1}", color="red", fontsize=10,
                              ha="center", va="bottom", zorder=10)

        if self.show_miller_indices and self.miller_indices_data:
            self.main_ax.axhline(y=self.miller_0_azimuth_ref, color="magenta",
                                 linestyle="--", lw=1, label="Miller 0° 基准线", zorder=5)
            for mi in self.miller_indices_data:
                m, = self.main_ax.plot(mi["q"], mi["azimuth"], "o",
                                       color="gray", markersize=4, alpha=0.7, zorder=10)
                self.miller_index_annotations.append(m)
            handles, labels = self.main_ax.get_legend_handles_labels()
            unique: dict = {}
            for h, l in zip(handles, labels):
                unique.setdefault(l, h)
            if unique:
                self.main_ax.legend(list(unique.values()), list(unique.keys()),
                                    loc="upper right", fontsize=8)

        self._update_selection_rectangle()
        if not is_default:
            self.main_ax.set_xlim(xlim)
            self.main_ax.set_ylim(ylim)
        else:
            self.main_ax.set_xlim(self.q_range)
            self.main_ax.set_ylim(self.azimuth_range)
        self.main_canvas.draw()

    def _create_marked_image(self, image_path: str) -> None:
        if self.image_data is None:
            return
        fig = Figure(figsize=(8, 6))
        ax  = fig.add_subplot(111)
        ax.imshow(self.image_data, aspect="auto", origin="lower",
                  cmap=ImageProcessor.matplotlib_cmap(self.current_colormap),
                  vmin=self.contrast_min, vmax=self.contrast_max,
                  extent=[self.q_range[0], self.q_range[1],
                          self.azimuth_range[0], self.azimuth_range[1]])
        ax.set_xlabel(r"q ($\AA^{-1}$)"); ax.set_ylabel("Azimuth (°)")
        ax.set_title("2D 积分图像 — 标记峰点")
        daz = self.azimuth_range[1] - self.azimuth_range[0]
        for i, pk in enumerate(self.recorded_peaks):
            ax.plot(pk["q"], pk["azimuth"], "x", color="red",
                    markersize=8, mew=2, alpha=0.8, zorder=10)
            ax.text(pk["q"], pk["azimuth"] + daz * 0.02, f"P{i+1}",
                    color="red", fontsize=10, ha="center", va="bottom", zorder=10)
        if self.show_miller_indices and self.miller_indices_data:
            ax.axhline(y=self.miller_0_azimuth_ref, color="magenta",
                       linestyle="--", lw=1, label="Miller 0° 基准线", zorder=5)
            for mi in self.miller_indices_data:
                ax.plot(mi["q"], mi["azimuth"], "o", color="gray",
                        markersize=4, alpha=0.7, zorder=10)
        fig.savefig(image_path, dpi=300, bbox_inches="tight")

    # ================================================================== #
    #  Display settings                                                    #
    # ================================================================== #

    def _update_colormap(self) -> None:
        self.current_colormap = self.colormap_combo.currentText()
        if self.image_data is not None:
            self._display_main_image()

    def _update_contrast(self) -> None:
        self.contrast_min = self.min_slider.value()
        self.contrast_max = self.max_slider.value()
        if self.contrast_min >= self.contrast_max:
            self.contrast_min = max(self.min_slider.minimum(), self.contrast_max - 1)
            self.min_slider.setValue(self.contrast_min)
        self.min_value_label.setText(f"Min: {self.contrast_min}")
        self.max_value_label.setText(f"Max: {self.contrast_max}")
        if self.image_data is not None:
            self._display_main_image()

    # ================================================================== #
    #  View crop / zoom                                                    #
    # ================================================================== #

    def _main_scroll(self, event) -> None:
        if self.image_data is None or event.xdata is None or event.ydata is None:
            return
        factor = 1.1 if event.button == "up" else 1 / 1.1
        cx, cy = event.xdata, event.ydata
        xl = self.main_ax.get_xlim(); yl = self.main_ax.get_ylim()
        self.main_ax.set_xlim([(x - cx) * factor + cx for x in xl])
        self.main_ax.set_ylim([(y - cy) * factor + cy for y in yl])
        self.main_canvas.draw()

    def _apply_quick_azimuth_range(self) -> None:
        if self.image_data is None:
            return
        ref  = self.miller_0_azimuth_spin.value()
        mode = self.miller_psi_convention_combo.currentData()
        s, e = -30.0, 120.0
        if mode == "0_horizontal_ccw":
            v1, v2 = ref + s, ref + e
        else:
            v1, v2 = ref - s, ref - e
        self.main_ax.set_ylim(min(v1, v2), max(v1, v2))
        self.main_canvas.draw()
        self._show_status(f"视图已裁剪: [{min(v1,v2):.1f}°, {max(v1,v2):.1f}°]")

    def _restore_full_view(self) -> None:
        if self.image_data is None:
            return
        self.main_ax.set_xlim(self.q_range)
        self.main_ax.set_ylim(self.azimuth_range)
        self.main_canvas.draw()

    # ================================================================== #
    #  Mouse interaction on main canvas                                    #
    # ================================================================== #

    def _main_mouse_press(self, event) -> None:
        if self.image_data is None or event.xdata is None or event.ydata is None:
            return
        q, az = event.xdata, event.ydata
        if self.selection_mode == "精准":
            self.slice_center_q = q
            self.slice_center_azimuth = az
            self.selected_q_peak_value = None
            self.selected_azimuth_peak_value = None
            self.found_q_peaks_list = []
            self.found_azimuth_peaks_list = []
            self._update_slice_plots()
            self._update_selection_info()
            self._update_selection_rectangle()
            self._update_record_btn_state()
        else:  # 粗略
            self.rough_selection_start_pos = (q, az)
            if self.current_selection_patch:
                try:
                    if self.current_selection_patch.axes:
                        self.current_selection_patch.remove()
                except Exception:
                    pass
                self.current_selection_patch = None
            self.current_selection_patch = patches.Rectangle(
                (q, az), 0, 0, lw=2, edgecolor="yellow", facecolor="none", ls="--"
            )
            self.main_ax.add_patch(self.current_selection_patch)
            self.main_canvas.draw()

    def _main_mouse_move(self, event) -> None:
        if self.image_data is None or event.xdata is None or event.ydata is None:
            return
        self._show_status(f"q: {event.xdata:.4f},  Azimuth: {event.ydata:.2f}°")
        if (self.selection_mode == "粗略" and
                self.rough_selection_start_pos and event.button == 1):
            sq, saz = self.rough_selection_start_pos
            w = event.xdata - sq; h = event.ydata - saz
            if self.current_selection_patch:
                self.current_selection_patch.set_xy(
                    (sq if w >= 0 else event.xdata, saz if h >= 0 else event.ydata)
                )
                self.current_selection_patch.set_width(abs(w))
                self.current_selection_patch.set_height(abs(h))
                self.main_canvas.draw()

    def _main_mouse_release(self, event) -> None:
        if self.image_data is None or event.xdata is None or event.ydata is None:
            return
        if self.selection_mode == "粗略" and self.rough_selection_start_pos:
            sq, saz = self.rough_selection_start_pos
            eq, eaz = event.xdata, event.ydata
            self.rough_selection_q_range      = (min(sq, eq), max(sq, eq))
            self.rough_selection_azimuth_range = (min(saz, eaz), max(saz, eaz))
            self.slice_center_q       = (sq + eq) / 2
            self.slice_center_azimuth = (saz + eaz) / 2
            self._clear_peak_selections()
            self._update_slice_plots()
            self._update_selection_info()
            self._update_selection_rectangle()
            self.rough_selection_start_pos = None
            self._update_record_btn_state()

    # ================================================================== #
    #  1D Slice plots                                                      #
    # ================================================================== #

    def _update_slice_plots(self) -> None:
        if (self.image_data is None or
                self.slice_center_q is None or self.slice_center_azimuth is None):
            for ax, canvas, title, xlabel in [
                (self.q_slice_ax,  self.q_slice_canvas,  "横向切片 (强度 vs q)",      r"q ($\AA^{-1}$)"),
                (self.az_slice_ax, self.az_slice_canvas, "纵向切片 (强度 vs 方位角)", "Azimuth (°)"),
            ]:
                ax.clear(); ax.set_title(title)
                ax.set_xlabel(xlabel); ax.set_ylabel("Intensity"); ax.grid(True)
                canvas.draw()
            return

        rows, cols = self.image_data.shape
        cq, caz = self.slice_center_q, self.slice_center_azimuth

        # ── q-slice ────────────────────────────────────────────────────
        az_int_w   = self.q_slice_int_width_spin.value()
        q_disp_rng = self.q_slice_disp_range_spin.value()

        _, py0 = self._coords_to_pixel(0, caz - az_int_w / 2)
        _, py1 = self._coords_to_pixel(0, caz + az_int_w / 2)
        r0 = int(np.clip(round(min(py0, py1)), 0, rows - 1))
        r1 = int(np.clip(round(max(py0, py1)), 0, rows - 1))
        slab_q = self.image_data[r0:r1+1, :]
        iq = np.mean(slab_q, axis=0) if slab_q.shape[0] > 0 else np.zeros(cols)
        qv = np.linspace(self.q_range[0], self.q_range[1], cols)

        self.q_slice_ax.clear()
        self.q_slice_ax.plot(qv, iq, "b-")
        if self.selected_q_peak_value is not None:
            idx = np.argmin(np.abs(qv - self.selected_q_peak_value))
            self.q_slice_ax.plot(qv[idx], iq[idx], "o", color="red", ms=8, mew=2, label="Selected Peak")
            self.q_slice_ax.axvline(self.selected_q_peak_value, color="red", ls=":", alpha=0.7)
        for pk in self.found_q_peaks_list:
            idx = np.argmin(np.abs(qv - pk["q"]))
            self.q_slice_ax.plot(qv[idx], iq[idx], "x", color="purple", ms=8, mew=2, label="Found Peak")
            self.q_slice_ax.axvline(pk["q"], color="purple", ls=":", alpha=0.7)

        self.q_slice_ax.set_title(f"强度 vs q  (Azimuth ≈ {caz:.1f}°, 积分宽度 {az_int_w}°)", fontsize=10)
        self.q_slice_ax.set_xlabel(r"q ($\AA^{-1}$)"); self.q_slice_ax.set_ylabel("Intensity")
        self.q_slice_ax.set_xlim(cq - q_disp_rng/2, cq + q_disp_rng/2)
        self.q_slice_ax.grid(True)
        vis = iq[(qv >= cq - q_disp_rng/2) & (qv <= cq + q_disp_rng/2)]
        if len(vis):
            rng = (np.max(vis) - np.min(vis)) or 1
            self.q_slice_ax.set_ylim(np.min(vis) - 0.05*rng, np.max(vis) + 0.05*rng)
        if self.selected_q_peak_value is not None or self.found_q_peaks_list:
            hs, ls = self.q_slice_ax.get_legend_handles_labels()
            ul: dict = {}
            for h, l in zip(hs, ls): ul.setdefault(l, h)
            if ul: self.q_slice_ax.legend(list(ul.values()), list(ul.keys()), loc="upper right")
        self.q_slice_canvas.draw()

        # ── azimuth-slice ───────────────────────────────────────────────
        q_int_w    = self.az_slice_int_width_spin.value()
        az_disp_rng = self.az_slice_disp_range_spin.value()

        px0, _ = self._coords_to_pixel(cq - q_int_w/2, 0)
        px1, _ = self._coords_to_pixel(cq + q_int_w/2, 0)
        c0 = int(np.clip(round(min(px0, px1)), 0, cols - 1))
        c1 = int(np.clip(round(max(px0, px1)), 0, cols - 1))
        slab_az = self.image_data[:, c0:c1+1]
        iaz = np.mean(slab_az, axis=1) if slab_az.shape[1] > 0 else np.zeros(rows)
        azv = np.linspace(self.azimuth_range[0], self.azimuth_range[1], rows)

        self.az_slice_ax.clear()
        self.az_slice_ax.plot(azv, iaz, "g-")
        if self.selected_azimuth_peak_value is not None:
            idx = np.argmin(np.abs(azv - self.selected_azimuth_peak_value))
            self.az_slice_ax.plot(azv[idx], iaz[idx], "o", color="blue", ms=8, mew=2, label="Selected Peak")
            self.az_slice_ax.axvline(self.selected_azimuth_peak_value, color="blue", ls=":", alpha=0.7)
        for pk in self.found_azimuth_peaks_list:
            idx = np.argmin(np.abs(azv - pk["azimuth"]))
            self.az_slice_ax.plot(azv[idx], iaz[idx], "x", color="purple", ms=8, mew=2, label="Found Peak")
            self.az_slice_ax.axvline(pk["azimuth"], color="purple", ls=":", alpha=0.7)

        self.az_slice_ax.set_title(f"强度 vs 方位角  (q ≈ {cq:.3f}, 积分宽度 {q_int_w:.3f})", fontsize=10)
        self.az_slice_ax.set_xlabel("Azimuth (°)"); self.az_slice_ax.set_ylabel("Intensity")
        self.az_slice_ax.set_xlim(caz - az_disp_rng/2, caz + az_disp_rng/2)
        self.az_slice_ax.grid(True)
        vis_az = iaz[(azv >= caz - az_disp_rng/2) & (azv <= caz + az_disp_rng/2)]
        if len(vis_az):
            rng = (np.max(vis_az) - np.min(vis_az)) or 1
            self.az_slice_ax.set_ylim(np.min(vis_az) - 0.05*rng, np.max(vis_az) + 0.05*rng)
        if self.selected_azimuth_peak_value is not None or self.found_azimuth_peaks_list:
            hs, ls = self.az_slice_ax.get_legend_handles_labels()
            ul: dict = {}
            for h, l in zip(hs, ls): ul.setdefault(l, h)
            if ul: self.az_slice_ax.legend(list(ul.values()), list(ul.keys()), loc="upper right")
        self.az_slice_canvas.draw()

    def _on_q_slice_click(self, event) -> None:
        if event.inaxes != self.q_slice_ax or event.xdata is None:
            return
        self.selected_q_peak_value = event.xdata
        self.found_q_peaks_list = []
        self.found_azimuth_peaks_list = []
        self._update_slice_plots()
        self._update_selection_info()
        self._update_selection_rectangle()
        self._update_record_btn_state()

    def _on_az_slice_click(self, event) -> None:
        if event.inaxes != self.az_slice_ax or event.xdata is None:
            return
        self.selected_azimuth_peak_value = event.xdata
        self.found_q_peaks_list = []
        self.found_azimuth_peaks_list = []
        self._update_slice_plots()
        self._update_selection_info()
        self._update_selection_rectangle()
        self._update_record_btn_state()

    # ================================================================== #
    #  Peak-finding                                                        #
    # ================================================================== #

    def _find_peaks_in_slices(self) -> None:
        if self.selection_mode != "粗略":
            QMessageBox.warning(self, "寻峰错误", "寻峰功能只在粗略选择模式下可用。")
            return
        if self.image_data is None:
            QMessageBox.warning(self, "寻峰错误", "请先加载 2D 积分图像。")
            return
        if self.rough_selection_q_range is None or self.rough_selection_azimuth_range is None:
            QMessageBox.warning(self, "寻峰错误", "请先在主图上拖拽选择一个粗略区域。")
            return

        rows, cols = self.image_data.shape
        qmin, qmax   = self.rough_selection_q_range
        azmin, azmax = self.rough_selection_azimuth_range
        prom  = self.peak_prominence_spin.value()
        width = self.peak_width_spin.value()

        self.found_q_peaks_list = []
        self.found_azimuth_peaks_list = []
        self.selected_q_peak_value = None
        self.selected_azimuth_peak_value = None

        # q-slice in rough region
        _, py0 = self._coords_to_pixel(0, azmin); _, py1 = self._coords_to_pixel(0, azmax)
        r0 = int(np.clip(round(min(py0, py1)), 0, rows - 1))
        r1 = int(np.clip(round(max(py0, py1)), 0, rows - 1))
        iq_full = np.mean(self.image_data[r0:r1+1, :], axis=0) if r1 >= r0 else np.zeros(cols)
        qv_full = np.linspace(self.q_range[0], self.q_range[1], cols)
        qi0 = int(np.clip(np.argmin(np.abs(qv_full - qmin)), 0, cols-1))
        qi1 = int(np.clip(np.argmin(np.abs(qv_full - qmax)), 0, cols-1))
        qi0, qi1 = min(qi0, qi1), max(qi0, qi1)
        if qi1 > qi0:
            pks, _ = find_peaks(iq_full[qi0:qi1+1], prominence=prom, width=width)
            for idx in pks:
                self.found_q_peaks_list.append(
                    {"q": qv_full[qi0+idx], "intensity": iq_full[qi0+idx]}
                )

        # azimuth-slice in rough region
        px0, _ = self._coords_to_pixel(qmin, 0); px1, _ = self._coords_to_pixel(qmax, 0)
        c0 = int(np.clip(round(min(px0, px1)), 0, cols - 1))
        c1 = int(np.clip(round(max(px0, px1)), 0, cols - 1))
        iaz_full = np.mean(self.image_data[:, c0:c1+1], axis=1) if c1 >= c0 else np.zeros(rows)
        azv_full = np.linspace(self.azimuth_range[0], self.azimuth_range[1], rows)
        ai0 = int(np.clip(np.argmin(np.abs(azv_full - azmin)), 0, rows-1))
        ai1 = int(np.clip(np.argmin(np.abs(azv_full - azmax)), 0, rows-1))
        ai0, ai1 = min(ai0, ai1), max(ai0, ai1)
        if ai1 > ai0:
            pks, _ = find_peaks(iaz_full[ai0:ai1+1], prominence=prom, width=width)
            for idx in pks:
                self.found_azimuth_peaks_list.append(
                    {"azimuth": azv_full[ai0+idx], "intensity": iaz_full[ai0+idx]}
                )

        self._update_slice_plots()
        self._update_selection_info()
        self._update_selection_rectangle()
        self._update_record_btn_state()
        self._show_status(
            f"在 q 切片中找到 {len(self.found_q_peaks_list)} 个峰，"
            f"在 Azimuth 切片中找到 {len(self.found_azimuth_peaks_list)} 个峰。"
        )

    # ================================================================== #
    #  Record management                                                   #
    # ================================================================== #

    def _record_found_peaks(self) -> None:
        if self.image_data is None:
            return

        def _intensity(q, az):
            px, py = self._coords_to_pixel(q, az)
            r, c = int(round(py)), int(round(px))
            if 0 <= r < self.image_data.shape[0] and 0 <= c < self.image_data.shape[1]:
                return float(self.image_data[r, c])
            return 0.0

        if self.selection_mode == "精准":
            if self.selected_q_peak_value is None or self.selected_azimuth_peak_value is None:
                QMessageBox.warning(self, "记录错误", "请先在切片图上选择一个峰。")
                return
            self.recorded_peaks.append({
                "q": self.selected_q_peak_value,
                "azimuth": self.selected_azimuth_peak_value,
                "intensity": _intensity(self.selected_q_peak_value,
                                        self.selected_azimuth_peak_value),
            })
            self._show_status(
                f"已记录峰: q={self.selected_q_peak_value:.4f}, "
                f"Azimuth={self.selected_azimuth_peak_value:.2f}°"
            )
        else:  # 粗略
            if not self.found_q_peaks_list and not self.found_azimuth_peaks_list:
                QMessageBox.warning(self, "记录错误", "没有找到任何峰值，请先寻峰。")
                return
            if self.found_q_peaks_list and self.found_azimuth_peaks_list:
                for qp in self.found_q_peaks_list:
                    for azp in self.found_azimuth_peaks_list:
                        self.recorded_peaks.append({
                            "q": qp["q"], "azimuth": azp["azimuth"],
                            "intensity": _intensity(qp["q"], azp["azimuth"]),
                        })
            elif self.found_q_peaks_list:
                for qp in self.found_q_peaks_list:
                    az = self.slice_center_azimuth or 0.0
                    self.recorded_peaks.append({
                        "q": qp["q"], "azimuth": az,
                        "intensity": _intensity(qp["q"], az),
                    })
            elif self.found_azimuth_peaks_list:
                for azp in self.found_azimuth_peaks_list:
                    q = self.slice_center_q or 0.0
                    self.recorded_peaks.append({
                        "q": q, "azimuth": azp["azimuth"],
                        "intensity": _intensity(q, azp["azimuth"]),
                    })
            self._show_status(f"已记录 {len(self.recorded_peaks)} 个峰。")

        self._update_record_list()
        self._display_main_image()

    def _update_record_list(self) -> None:
        self.record_list.clear()
        for i, pk in enumerate(self.recorded_peaks):
            text = (f"峰 {i+1}: q={pk['q']:.4f} Å⁻¹,  "
                    f"Azimuth={pk['azimuth']:.2f}°,  强度={pk['intensity']:.2f}")
            self.record_list.addItem(QListWidgetItem(text))

    def _delete_selected_record(self) -> None:
        selected = self.record_list.selectedItems()
        if not selected:
            return
        reply = QMessageBox.question(self, "确认删除", "确定要删除选中的峰记录吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return
        for idx in sorted([self.record_list.row(i) for i in selected], reverse=True):
            del self.recorded_peaks[idx]
        self._update_record_list()
        self._display_main_image()

    def _clear_all_records(self) -> None:
        if not self.recorded_peaks:
            return
        reply = QMessageBox.question(self, "确认清空", "确定要删除所有已记录的峰吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.recorded_peaks.clear()
            self._update_record_list()
            self._display_main_image()

    # ================================================================== #
    #  Selection helpers                                                   #
    # ================================================================== #

    def _update_selection_mode(self) -> None:
        if self.precise_radio.isChecked():
            self.selection_mode = "精准"
            self.peak_finding_grp.setEnabled(False)
            self.find_peaks_btn.setEnabled(False)
            self._show_status("模式: 精准选择。点击主图定切片，点击切片图选择峰。")
        else:
            self.selection_mode = "粗略"
            self.peak_finding_grp.setEnabled(True)
            self.find_peaks_btn.setEnabled(True)
            self._show_status("模式: 粗略选择。在主图上按住拖动选择区域。")
        self._clear_current_selection()
        self._update_record_btn_state()

    def _clear_peak_selections(self) -> None:
        self.selected_q_peak_value = None
        self.selected_azimuth_peak_value = None
        self.found_q_peaks_list = []
        self.found_azimuth_peaks_list = []

    def _clear_current_selection(self) -> None:
        self.slice_center_q = None
        self.slice_center_azimuth = None
        self.rough_selection_q_range = None
        self.rough_selection_azimuth_range = None
        self.rough_selection_start_pos = None
        self._clear_peak_selections()

        if self.current_selection_patch:
            try:
                if self.current_selection_patch.axes:
                    self.current_selection_patch.remove()
            except Exception:
                pass
            self.current_selection_patch = None

        self._update_slice_plots()
        self._update_selection_info()
        self._display_main_image()
        self._update_record_btn_state()
        self._show_status("当前选择已清除。")

    def _update_selection_info(self) -> None:
        # Label intentionally left empty (kept for future extension)
        self.selection_info_label.setText("")

    def _update_selection_rectangle(self) -> None:
        if self.current_selection_patch:
            try:
                if self.current_selection_patch.axes:
                    self.current_selection_patch.remove()
            except Exception:
                pass
            self.current_selection_patch = None

        if self.image_data is None:
            self.main_canvas.draw()
            return

        if self.selection_mode == "精准":
            if self.slice_center_q is not None and self.slice_center_azimuth is not None:
                r = (self.q_range[1] - self.q_range[0]) * 0.005
                self.current_selection_patch = patches.Circle(
                    (self.slice_center_q, self.slice_center_azimuth),
                    radius=r, lw=2, edgecolor="cyan", facecolor="none",
                )
                self.main_ax.add_patch(self.current_selection_patch)
            if (self.selected_q_peak_value is not None and
                    self.selected_azimuth_peak_value is not None):
                self.main_ax.plot(self.selected_q_peak_value, self.selected_azimuth_peak_value,
                                  "o", color="red", ms=10, mew=2, fillstyle="none", zorder=10)
        else:
            if self.rough_selection_q_range and self.rough_selection_azimuth_range:
                qlo, qhi   = self.rough_selection_q_range
                azlo, azhi = self.rough_selection_azimuth_range
                self.current_selection_patch = patches.Rectangle(
                    (qlo, azlo), qhi - qlo, azhi - azlo,
                    lw=2, edgecolor="yellow", facecolor="none", ls="--",
                )
                self.main_ax.add_patch(self.current_selection_patch)
            if self.found_q_peaks_list and self.found_azimuth_peaks_list:
                for qp in self.found_q_peaks_list:
                    for azp in self.found_azimuth_peaks_list:
                        self.main_ax.plot(qp["q"], azp["azimuth"],
                                          "x", color="purple", ms=10, mew=2, zorder=10)
        self.main_canvas.draw()

    def _update_record_btn_state(self) -> None:
        if self.selection_mode == "精准":
            self.record_peaks_btn.setEnabled(
                self.selected_q_peak_value is not None and
                self.selected_azimuth_peak_value is not None
            )
        else:
            self.record_peaks_btn.setEnabled(
                bool(self.found_q_peaks_list or self.found_azimuth_peaks_list)
            )

    # ================================================================== #
    #  Miller indices                                                      #
    # ================================================================== #

    def _miller_azimuth_in_image(self, miller_psi: float) -> float:
        """Convert a Miller ψ angle to the image Azimuth coordinate system."""
        ref  = self.miller_0_azimuth_ref
        mode = self.psi_convention_mode
        norm = (miller_psi % 360 + 360) % 360
        if mode == "0_horizontal_ccw":
            az = -norm - ref
        else:  # cw
            az = norm + ref
        return normalize_angle_to_180(az)

    def _toggle_miller_display(self, checked: bool) -> None:
        self.show_miller_indices = checked
        self._display_main_image()
        self._show_status(f"米勒指数显示已{'启用' if checked else '禁用'}。")

    def _update_miller_settings(self) -> None:
        self.psi_convention_mode  = self.miller_psi_convention_combo.currentData()
        self.miller_0_azimuth_ref = self.miller_0_azimuth_spin.value()
        if self._original_miller_indices_data:
            self.miller_indices_data = [
                {
                    "q": mi["q"],
                    "azimuth": self._miller_azimuth_in_image(mi["original_psi"]),
                    "hkl": mi["hkl"],
                    "original_psi": mi["original_psi"],
                }
                for mi in self._original_miller_indices_data
            ]
        self._display_main_image()
