"""
raw_image_tab.py  –  原始衍射图像分析选项卡 (2D-WAXS 衍射斑点位置确定).

Loads raw EDF / TIFF detector images, shows a zoom view around a clicked
pixel, integrates via pyFAI, and lets the user record (q, ψ) peak positions.
"""

from __future__ import annotations

import csv
import math
import os
import traceback

import fabio
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor, QFont, QIcon, QImage, QPainter, QPen, QPixmap,
)
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame,
    QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox,
    QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from .image_processor import ImageProcessor
from .styles import AppStyles

try:
    import pyFAI
    _PYFAI_OK = True
except ImportError:
    _PYFAI_OK = False


class RawImageTab(QWidget):
    """Widget for raw detector image peak picking (原始图像提取点).

    Embed this widget inside a ``QTabWidget`` in the main window.
    The *status_bar* parameter should be the ``QMainWindow.statusBar()``
    instance so this tab can post messages to the shared status bar.
    """

    def __init__(self, status_bar, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._status_bar = status_bar
        self._previous_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._repo_root = os.path.dirname(self._previous_root)

        # ── image data ──────────────────────────────────────────────────
        self.original_image: np.ndarray | None = None
        self.display_image: np.ndarray | None = None
        self.threshold_min: float = 0
        self.threshold_max: float = 65535

        # ── selection state ─────────────────────────────────────────────
        self.current_point: tuple[int, int] | None = None
        self.current_zoom_point: dict | None = None
        self.current_x: int = 0
        self.current_y: int = 0
        self.current_q: float | None = None
        self.current_psi: float | None = None
        self.selected_q: float | None = None
        self.selected_psi: float | None = None

        # ── recorded data ───────────────────────────────────────────────
        self.recorded_points: list[dict] = []

        # ── zoom / pan ──────────────────────────────────────────────────
        self.zoom_factor: float = 1.0
        self.zoom_step: float = 0.1
        self.min_zoom: float = 0.1
        self.max_zoom: float = 5.0
        self.zoom_size: int = 30

        # ── instrument parameters ────────────────────────────────────────
        self.wavelength: float = 1.0          # Å
        self.pixel_size_x: float = 100.0      # µm
        self.pixel_size_y: float = 100.0      # µm
        self.center_x: float = 0.0            # pixel
        self.center_y: float = 0.0            # pixel
        self.detector_distance: float = 1000.0  # mm

        # ── display ─────────────────────────────────────────────────────
        self.contrast_mode: str = "Linear"
        self.contrast_min: float = 0
        self.contrast_max: float = 65535
        self.current_colormap: str = "灰度"

        # ── pyFAI integrator ─────────────────────────────────────────────
        self.ai = None

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
        splitter.setSizes([1500, 100])

    # ── Left panel ─────────────────────────────────────────────────────

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(5, 5, 5, 5)
        w.setMinimumWidth(400)
        w.setMaximumWidth(1200)

        # Main image
        img_grp = QGroupBox("图像显示")
        img_grp.setStyleSheet(AppStyles.IMAGE_GROUP)
        img_lay = QVBoxLayout(img_grp)

        self.main_scene = QGraphicsScene()
        self.main_view = QGraphicsView(self.main_scene)
        self.main_view.setMouseTracking(True)
        self.main_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.main_view.mousePressEvent = self._main_image_clicked
        self.main_view.wheelEvent = self._wheel_event

        reset_btn = QPushButton("重置缩放")
        reset_btn.setStyleSheet(AppStyles.BUTTON)
        reset_btn.clicked.connect(self._reset_zoom)

        img_lay.addWidget(self.main_view, 4)
        img_lay.addWidget(reset_btn)
        lay.addWidget(img_grp, 4)

        # Contrast / display settings
        ct_grp = QGroupBox("对比度设置")
        ct_grp.setStyleSheet(AppStyles.SETTINGS_GROUP)
        ct_lay = QVBoxLayout(ct_grp)

        min_row = QHBoxLayout()
        min_row.addWidget(QLabel("最小值:"))
        self.min_slider = QSlider(Qt.Orientation.Horizontal)
        self.min_slider.setRange(0, 65535)
        self.min_slider.setValue(0)
        self.min_slider.valueChanged.connect(self._update_contrast)
        min_row.addWidget(self.min_slider)
        self.min_value_label = QLabel("0")
        min_row.addWidget(self.min_value_label)
        ct_lay.addLayout(min_row)

        max_row = QHBoxLayout()
        max_row.addWidget(QLabel("最大值:"))
        self.max_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_slider.setRange(0, 65535)
        self.max_slider.setValue(65535)
        self.max_slider.valueChanged.connect(self._update_contrast)
        max_row.addWidget(self.max_slider)
        self.max_value_label = QLabel("65535")
        max_row.addWidget(self.max_value_label)
        ct_lay.addLayout(max_row)

        zoom_row = QHBoxLayout()
        zoom_row.addWidget(QLabel("放大区域大小:"))
        self.zoom_size_combo = QComboBox()
        self.zoom_size_combo.addItems(["30x30", "50x50", "100x100"])
        self.zoom_size_combo.currentIndexChanged.connect(self._update_zoom_size)
        zoom_row.addWidget(self.zoom_size_combo)
        ct_lay.addLayout(zoom_row)

        lay.addWidget(ct_grp)
        return w

    # ── Right panel ────────────────────────────────────────────────────

    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(5, 5, 5, 5)

        tabs = QTabWidget()
        tabs.setStyleSheet(AppStyles.TAB_WIDGET)
        lay.addWidget(tabs)

        tabs.addTab(self._build_tab_settings(), "1.图像设置")
        tabs.addTab(self._build_tab_analysis(), "2.图像分析")
        tabs.addTab(self._build_tab_records(), "3.数据列表")
        return w

    # ── Tab 0: Settings ────────────────────────────────────────────────

    def _build_tab_settings(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)

        # File import
        file_grp = QGroupBox("导入文件")
        file_grp.setStyleSheet(AppStyles.GROUP)
        file_lay = QVBoxLayout(file_grp)
        file_lay.setSpacing(1)

        btn_row = QHBoxLayout()
        open_btn = QPushButton("打开图像文件")
        open_btn.setStyleSheet(AppStyles.BUTTON)
        open_btn.setIcon(QIcon.fromTheme("document-open"))
        open_btn.setToolTip("打开 EDF 或 TIFF 格式的衍射图像")
        open_btn.clicked.connect(self.open_file)
        btn_row.addWidget(open_btn, stretch=2)

        poni_btn = QPushButton("导入 PONI 文件")
        poni_btn.setStyleSheet(AppStyles.BUTTON)
        poni_btn.setToolTip("导入 pyFAI 生成的 PONI 标定文件")
        poni_btn.clicked.connect(self.import_poni_file)
        btn_row.addWidget(poni_btn, stretch=1)
        file_lay.addLayout(btn_row)
        lay.addWidget(file_grp)

        # Image / mask settings
        photo_grp = QGroupBox("图像显示及 Mask 设置")
        photo_grp.setStyleSheet(AppStyles.GROUP)
        photo_lay = QVBoxLayout(photo_grp)

        thr_row = QHBoxLayout()
        self.min_threshold_edit = QLineEdit("0")
        self.max_threshold_edit = QLineEdit("65535")
        apply_thr_btn = QPushButton("应用阈值 (Mask)")
        apply_thr_btn.clicked.connect(self._apply_threshold)
        thr_row.addWidget(QLabel("Min:"))
        thr_row.addWidget(self.min_threshold_edit)
        thr_row.addWidget(QLabel("Max:"))
        thr_row.addWidget(self.max_threshold_edit)
        thr_row.addWidget(apply_thr_btn)
        photo_lay.addLayout(thr_row)

        auto_thr_btn = QPushButton("自动阈值")
        auto_thr_btn.clicked.connect(self._calculate_auto_threshold)
        photo_lay.addWidget(auto_thr_btn)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("对比度模式:"))
        self.contrast_mode_combo = QComboBox()
        self.contrast_mode_combo.addItems(["Linear"])
        self.contrast_mode_combo.currentIndexChanged.connect(self._update_contrast_mode)
        mode_row.addWidget(self.contrast_mode_combo)
        photo_lay.addLayout(mode_row)

        cmap_row = QHBoxLayout()
        cmap_row.addWidget(QLabel("颜色映射:"))
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(["灰度", "反转灰度", "热力图", "彩虹"])
        self.colormap_combo.currentIndexChanged.connect(self._update_colormap)
        cmap_row.addWidget(self.colormap_combo)
        photo_lay.addLayout(cmap_row)
        lay.addWidget(photo_grp)

        # Instrument parameters
        phys_grp = QGroupBox("仪器参数设置")
        phys_grp.setStyleSheet(AppStyles.GROUP)
        phys_form = QFormLayout()

        self.wavelength_edit    = QLineEdit("1.0")
        self.pixel_size_x_edit  = QLineEdit("100")
        self.pixel_size_y_edit  = QLineEdit("100")
        self.center_x_edit      = QLineEdit("0")
        self.center_y_edit      = QLineEdit("0")
        self.distance_edit      = QLineEdit("1000")

        phys_form.addRow("波长 (Å):",         self.wavelength_edit)
        phys_form.addRow("像素大小 X (µm):",   self.pixel_size_x_edit)
        phys_form.addRow("像素大小 Y (µm):",   self.pixel_size_y_edit)
        phys_form.addRow("中心 X (pixel):",    self.center_x_edit)
        phys_form.addRow("中心 Y (pixel):",    self.center_y_edit)
        phys_form.addRow("探测器距离 (mm):",   self.distance_edit)
        phys_grp.setLayout(phys_form)
        lay.addWidget(phys_grp)

        # Info / about
        info_grp = QGroupBox()
        info_grp.setStyleSheet(AppStyles.INFO_GROUP)
        info_lay = QVBoxLayout(info_grp)

        usage_lbl = QLabel("""
<h3>使用说明</h3>
<ol>
<li><b>导入衍射图像</b>：支持 .edf 和 .tiff 格式</li>
<li><b>导入标定文件</b>：使用 pyFAI 生成的 poni 文件，或手动输入参数</li>
<li><b>图像处理</b>：在左侧图像中点击选择衍射峰，在右侧面板筛选最大值</li>
<li><b>导出数据</b>：生成 CSV 格式文件用于后续分析</li>
</ol>
""")
        usage_lbl.setWordWrap(True)
        usage_lbl.setStyleSheet("font-size: 10pt; color: #103d7e;")
        info_lay.addWidget(usage_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        info_lay.addWidget(sep)

        ack_lbl = QLabel("""
<h3>致谢</h3>
<ul>
<li>pyFAI 开发团队</li>
<li>PySide6 / Qt</li>
<li>中国科学院化学研究所 / 工程塑料实验室</li>
</ul>
<p style="font-style:italic;color:#555;">联系: tyma507@iccas.ac.cn</p>
""")
        ack_lbl.setWordWrap(True)
        ack_lbl.setStyleSheet("font-size: 10pt; color: #103d7e;")
        info_lay.addWidget(ack_lbl)

        # Logo row
        logos_w = QWidget()
        logos_row = QHBoxLayout(logos_w)
        logos_row.setContentsMargins(0, 0, 0, 0)

        for logo_path, label_text in [
            ("logo/ICCAS.jpg", "中国科学院化学研究所"),
            ("logo/EP.png",    "工程塑料实验室"),
        ]:
            container = QWidget()
            c_lay = QVBoxLayout(container)
            c_lay.setContentsMargins(0, 0, 0, 0)
            logo_lbl = QLabel()
            pm = QPixmap(self._resolve_logo_path(logo_path, label_text))
            if not pm.isNull():
                logo_lbl.setPixmap(
                    pm.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
                )
            logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c_lay.addWidget(logo_lbl)
            txt = QLabel(label_text)
            txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            txt.setStyleSheet("font-size: 9pt; color: #555;")
            c_lay.addWidget(txt)
            logos_row.addWidget(container)

        info_lay.addWidget(logos_w)
        lay.addWidget(info_grp)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        return scroll

    def _resolve_logo_path(self, logo_path: str, label_text: str) -> str:
        candidates = [
            os.path.join(self._previous_root, logo_path),
        ]

        fallback_name = "index.jpg" if "研究所" in label_text else "favicon.ico"
        candidates.append(os.path.join(self._repo_root, "icon", fallback_name))
        candidates.append(os.path.join(self._repo_root, "icon", "index.jpg"))

        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate

        return ""

    # ── Tab 1: Analysis ────────────────────────────────────────────────

    def _build_tab_analysis(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)

        # Zoom view
        zoom_grp = QGroupBox("放大视图")
        zoom_grp.setStyleSheet(AppStyles.GROUP)
        zoom_grp.setMaximumHeight(250)
        zoom_lay = QVBoxLayout(zoom_grp)

        self.zoom_scene = QGraphicsScene()
        self.zoom_view = QGraphicsView(self.zoom_scene)
        self.zoom_view.setMouseTracking(True)
        self.zoom_view.mousePressEvent = self._zoom_image_clicked
        zoom_lay.addWidget(self.zoom_view)

        self.zoom_info = QLabel("放大区域信息将显示在这里")
        self.zoom_info.setStyleSheet(
            "color:#103d7e; background-color:#ebfaff; padding:8px; "
            "border-radius:4px; font-size:10px;"
        )
        zoom_lay.addWidget(self.zoom_info)

        self.record_btn = QPushButton("记录当前点")
        self.record_btn.setStyleSheet(AppStyles.BUTTON)
        self.record_btn.clicked.connect(self._record_current_point)
        self.record_btn.setEnabled(False)
        zoom_lay.addWidget(self.record_btn)
        lay.addWidget(zoom_grp)

        # Integration analysis
        intg_grp = QGroupBox("积分分析")
        intg_grp.setStyleSheet(AppStyles.GROUP)
        intg_lay = QVBoxLayout(intg_grp)

        # q-I parameters
        param_q_lay = QHBoxLayout()
        param_q_lay.addWidget(self._bold_label("q-I 参数设置:"))

        self.azimuth_range_spin = QDoubleSpinBox()
        self.azimuth_range_spin.setRange(1, 90); self.azimuth_range_spin.setValue(5)
        self.azimuth_range_spin.setSingleStep(5)
        self.azimuth_range_spin.valueChanged.connect(self._update_integration)
        param_q_lay.addWidget(QLabel("Azimuth Range (±°):"))
        param_q_lay.addWidget(self.azimuth_range_spin)

        self.radial_range_spin = QDoubleSpinBox()
        self.radial_range_spin.setRange(0.01, 1.0); self.radial_range_spin.setValue(0.35)
        self.radial_range_spin.setSingleStep(0.02)
        self.radial_range_spin.valueChanged.connect(self._update_integration)
        param_q_lay.addWidget(QLabel("Radial Range (±Å⁻¹):"))
        param_q_lay.addWidget(self.radial_range_spin)

        self.npt_spin = QSpinBox()
        self.npt_spin.setRange(10, 5000); self.npt_spin.setValue(500)
        self.npt_spin.valueChanged.connect(self._update_integration)
        param_q_lay.addWidget(QLabel("Q Points:"))
        param_q_lay.addWidget(self.npt_spin)

        self.npt_rad_spin = QSpinBox()
        self.npt_rad_spin.setRange(1, 5000); self.npt_rad_spin.setValue(30)
        self.npt_rad_spin.valueChanged.connect(self._update_integration)
        param_q_lay.addWidget(QLabel("Psi Points:"))
        param_q_lay.addWidget(self.npt_rad_spin)
        intg_lay.addLayout(param_q_lay)

        # ψ-I parameters
        param_psi_lay = QHBoxLayout()
        param_psi_lay.addWidget(self._bold_label("ψ-I 参数设置:"))

        self.azimuth_range_spin_r = QDoubleSpinBox()
        self.azimuth_range_spin_r.setRange(1, 90); self.azimuth_range_spin_r.setValue(30)
        self.azimuth_range_spin_r.setSingleStep(0.5)
        self.azimuth_range_spin_r.valueChanged.connect(self._update_integration)
        param_psi_lay.addWidget(QLabel("Azimuth Range (±°):"))
        param_psi_lay.addWidget(self.azimuth_range_spin_r)

        self.radial_range_spin_r = QDoubleSpinBox()
        self.radial_range_spin_r.setRange(0.01, 1.0); self.radial_range_spin_r.setValue(0.05)
        self.radial_range_spin_r.setSingleStep(0.02)
        self.radial_range_spin_r.valueChanged.connect(self._update_integration)
        param_psi_lay.addWidget(QLabel("Radial Range (±Å⁻¹):"))
        param_psi_lay.addWidget(self.radial_range_spin_r)

        self.npt_spin_r = QSpinBox()
        self.npt_spin_r.setRange(10, 500); self.npt_spin_r.setValue(50)
        self.npt_spin_r.valueChanged.connect(self._update_integration)
        param_psi_lay.addWidget(QLabel("Q Points:"))
        param_psi_lay.addWidget(self.npt_spin_r)

        self.npt_rad_spin_r = QSpinBox()
        self.npt_rad_spin_r.setRange(1, 5000); self.npt_rad_spin_r.setValue(150)
        self.npt_rad_spin_r.valueChanged.connect(self._update_integration)
        param_psi_lay.addWidget(QLabel("Psi Points:"))
        param_psi_lay.addWidget(self.npt_rad_spin_r)
        intg_lay.addLayout(param_psi_lay)

        # Matplotlib canvas
        self.integration_figure = Figure()
        self.integration_canvas = FigureCanvas(self.integration_figure)
        intg_lay.addWidget(self.integration_canvas)

        calc_btn = QPushButton("计算选中曲线下新的像素点")
        calc_btn.setStyleSheet(AppStyles.BUTTON)
        calc_btn.clicked.connect(self._calculate_new_pixel)
        intg_lay.addWidget(calc_btn)
        lay.addWidget(intg_grp)
        return tab

    # ── Tab 2: Records ─────────────────────────────────────────────────

    def _build_tab_records(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)

        rec_grp = QGroupBox("记录点列表")
        rec_grp.setStyleSheet(AppStyles.GROUP)
        rec_lay = QVBoxLayout(rec_grp)

        self.record_list = QListWidget()
        rec_lay.addWidget(self.record_list)

        del_btn = QPushButton("删除选中记录")
        del_btn.setStyleSheet(AppStyles.BUTTON)
        del_btn.clicked.connect(self._delete_selected_record)
        rec_lay.addWidget(del_btn)

        export_btn = QPushButton("记录点击点")
        export_btn.setStyleSheet(AppStyles.BUTTON)
        export_btn.clicked.connect(self.export_recorded_points)
        rec_lay.addWidget(export_btn)

        clear_btn = QPushButton("删除所有记录")
        clear_btn.setStyleSheet(AppStyles.BUTTON)
        clear_btn.clicked.connect(self._clear_all_records)
        rec_lay.addWidget(clear_btn)

        lay.addWidget(rec_grp, 2)
        return tab

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _bold_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold;")
        return lbl

    def _show_status(self, msg: str) -> None:
        self._status_bar.showMessage(msg)

    # ================================================================== #
    #  File I/O                                                            #
    # ================================================================== #

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "打开图像", "", "图像文件 (*.tiff *.tif *.edf)"
        )
        if path:
            self._load_image(path)

    def import_poni_file(self) -> None:
        """Load a pyFAI PONI calibration file and populate instrument fields."""
        if not _PYFAI_OK:
            QMessageBox.warning(self, "错误", "未安装 pyFAI，无法导入 PONI 文件")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "导入 PONI 文件", "", "PONI 文件 (*.poni)"
        )
        if not path:
            return

        try:
            ai = pyFAI.load(path)

            pixel_y = ai.detector.pixel1 * 1e6 if hasattr(ai.detector, "pixel1") else 100.0
            pixel_x = ai.detector.pixel2 * 1e6 if hasattr(ai.detector, "pixel2") else 100.0
            center_x = ai.poni2 / (ai.detector.pixel2 or 1e-6)
            center_y = ai.poni1 / (ai.detector.pixel1 or 1e-6)
            distance = ai.dist * 1e3
            wavelength = ai.wavelength * 1e10

            self.wavelength_edit.setText(f"{wavelength:.6f}")
            self.pixel_size_x_edit.setText(f"{pixel_x:.2f}")
            self.pixel_size_y_edit.setText(f"{pixel_y:.2f}")
            self.center_x_edit.setText(f"{center_x:.2f}")
            self.center_y_edit.setText(f"{center_y:.2f}")
            self.distance_edit.setText(f"{distance:.2f}")

            self._show_status(f"已导入 PONI 文件: {path}")
            QMessageBox.information(self, "导入成功", "PONI 文件参数已成功导入")

            if self.display_image is not None:
                self._display_main_image()

        except Exception as exc:
            QMessageBox.critical(self, "导入错误", f"导入 PONI 文件时出错:\n{exc}")

    def export_recorded_points(self) -> None:
        """Export recorded (q, ψ) points to CSV and save a marked PNG."""
        if not self.recorded_points:
            QMessageBox.warning(self, "导出错误", "没有记录的点可导出")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "导出记录点", "", "CSV 文件 (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=["index", "q", "psi_degrees"])
                writer.writeheader()
                for i, pt in enumerate(self.recorded_points):
                    if "q" in pt and "psi" in pt:
                        writer.writerow({
                            "index": i + 1,
                            "q": pt["q"],
                            "psi_degrees": math.degrees(pt["psi"]),
                        })

            img_path = os.path.splitext(path)[0] + "_marked.png"
            self._create_marked_image(img_path)

            self._show_status(f"已导出到: {path} 和 {img_path}")
            QMessageBox.information(
                self, "导出成功",
                f"记录点已成功导出\nCSV: {path}\n标记图像: {img_path}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "导出错误", f"导出时出错:\n{exc}")

    # ================================================================== #
    #  Image loading & display                                             #
    # ================================================================== #

    def _load_image(self, file_path: str) -> None:
        try:
            img = fabio.open(file_path)
            self.original_image = img.data
            self.display_image = self.original_image.copy()
            self._calculate_auto_threshold()

            if self.original_image.size > 50:
                top50 = np.partition(self.original_image.flatten(), -50)[-50:]
                contrast_max = int(np.median(top50))
                lo = int(np.min(self.original_image))
                hi = int(np.max(self.original_image))
                self.min_slider.setRange(lo, hi)
                self.max_slider.setRange(lo, hi)
                self.min_slider.setValue(lo)
                self.max_slider.setValue(contrast_max)
                self.min_value_label.setText(str(lo))
                self.max_value_label.setText(str(contrast_max))
                self.contrast_min = lo
                self.contrast_max = contrast_max

            self._display_main_image()
            self._show_status(f"已加载: {file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "加载错误", f"无法加载图像:\n{exc}")

    def _display_main_image(self) -> None:
        if self.display_image is None:
            return
        self.main_scene.clear()

        qimg = ImageProcessor.apply_colormap(
            self.display_image, self.current_colormap,
            self.contrast_min, self.contrast_max, self.contrast_mode
        )
        pixmap = QPixmap.fromImage(qimg)
        self.main_scene.addItem(QGraphicsPixmapItem(pixmap))

        try:
            cx = float(self.center_x_edit.text())
            cy = float(self.center_y_edit.text())
            pen = QPen(QColor(255, 255, 0), 2)
            self.main_scene.addLine(cx - 10, cy, cx + 10, cy, pen)
            self.main_scene.addLine(cx, cy - 10, cx, cy + 10, pen)
        except ValueError:
            pass

        for pt in self.recorded_points:
            self._draw_point_on_main_image(pt["x"], pt["y"])

    def _create_marked_image(self, image_path: str) -> None:
        if self.display_image is None:
            return
        qimg = ImageProcessor.apply_colormap(
            self.display_image, self.current_colormap,
            self.contrast_min, self.contrast_max, self.contrast_mode
        )
        pixmap = QPixmap.fromImage(qimg)
        painter = QPainter(pixmap)

        cx = float(self.center_x_edit.text() or "0")
        cy = float(self.center_y_edit.text() or "0")
        painter.setPen(QPen(QColor(255, 255, 0), 2))
        painter.drawLine(int(cx) - 10, int(cy), int(cx) + 10, int(cy))
        painter.drawLine(int(cx), int(cy) - 10, int(cx), int(cy) + 10)

        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        for i, pt in enumerate(self.recorded_points):
            x, y = int(pt["x"]), int(pt["y"])
            painter.drawRect(x - 2, y - 2, 4, 4)
            painter.drawText(x + 5, y - 5, str(i + 1))

        painter.end()
        pixmap.save(image_path)

    # ================================================================== #
    #  Threshold / contrast / colormap                                     #
    # ================================================================== #

    def _calculate_auto_threshold(self) -> None:
        if self.original_image is None:
            return
        if self.original_image.size > 50:
            top50 = np.partition(self.original_image.flatten(), -50)[-50:]
            thr_max = (np.median(top50) + np.max(top50)) / 2
            self.min_threshold_edit.setText("0")
            self.max_threshold_edit.setText(str(int(thr_max)))
            self.threshold_min = 0
            self.threshold_max = thr_max
            mask = (self.original_image < 0) | (self.original_image > thr_max)
            self.display_image = np.where(mask, 0, self.original_image)
            self._display_main_image()
            self._show_status(f"应用自动阈值: 0 – {thr_max:.2f}")

    def _apply_threshold(self) -> None:
        try:
            lo = float(self.min_threshold_edit.text())
            hi = float(self.max_threshold_edit.text())
            if lo >= hi:
                QMessageBox.warning(self, "阈值错误", "最小值必须小于最大值")
                return
            self.threshold_min = lo
            self.threshold_max = hi
            if self.original_image is not None:
                mask = (self.original_image < lo) | (self.original_image > hi)
                self.display_image = np.where(mask, 0, self.original_image)
                self._display_main_image()
                self._show_status(f"应用阈值: {lo} – {hi}")
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的数字阈值")

    def _update_contrast(self) -> None:
        self.contrast_min = self.min_slider.value()
        self.contrast_max = self.max_slider.value()
        self.min_value_label.setText(str(self.contrast_min))
        self.max_value_label.setText(str(self.contrast_max))
        self._display_main_image()

    def _update_contrast_mode(self) -> None:
        self.contrast_mode = self.contrast_mode_combo.currentText()
        self._display_main_image()

    def _update_colormap(self) -> None:
        self.current_colormap = self.colormap_combo.currentText()
        self._display_main_image()

    def _update_zoom_size(self) -> None:
        self.zoom_size = int(self.zoom_size_combo.currentText().split("x")[0])
        if self.current_point:
            self._show_zoom_view(*self.current_point)

    # ================================================================== #
    #  Zoom / view controls                                                #
    # ================================================================== #

    def _reset_zoom(self) -> None:
        self.zoom_factor = 1.0
        self.main_view.resetTransform()
        self._show_status("缩放已重置")

    def _wheel_event(self, event) -> None:
        if self.original_image is None:
            return
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_factor = min(self.zoom_factor * (1 + self.zoom_step), self.max_zoom)
        else:
            self.zoom_factor = max(self.zoom_factor * (1 - self.zoom_step), self.min_zoom)
        self.main_view.resetTransform()
        self.main_view.scale(self.zoom_factor, self.zoom_factor)
        self._show_status(f"缩放: {self.zoom_factor:.1f}×")

    # ================================================================== #
    #  Mouse interaction                                                   #
    # ================================================================== #

    def _main_image_clicked(self, event) -> None:
        if self.display_image is None:
            return
        scene_pos = self.main_view.mapToScene(event.pos())
        x, y = int(scene_pos.x()), int(scene_pos.y())
        h, w = self.display_image.shape
        if 0 <= x < w and 0 <= y < h:
            self.current_point = (x, y)
            self._show_zoom_view(x, y)

    def _zoom_image_clicked(self, event) -> None:
        if self.original_image is None or self.current_point is None:
            return
        scene_pos = self.zoom_view.mapToScene(event.pos())
        x_local, y_local = int(scene_pos.x()), int(scene_pos.y())

        h, w = self.original_image.shape
        half = self.zoom_size // 2
        x_glob = max(0, min(w - 1, self.current_point[0] - half + x_local))
        y_glob = max(0, min(h - 1, self.current_point[1] - half + y_local))
        intensity = self.original_image[y_glob, x_glob]

        self.current_zoom_point = {"x": x_glob, "y": y_glob, "intensity": intensity}

        # Redraw zoom view with green marker
        self.zoom_scene.clear()
        x, y = self.current_point
        x1 = max(0, x - half); y1 = max(0, y - half)
        x2 = min(w, x + half); y2 = min(h, y + half)
        zone = self.original_image[y1:y2, x1:x2]
        qimg = ImageProcessor.apply_colormap(
            zone, self.current_colormap,
            self.contrast_min, self.contrast_max, self.contrast_mode
        )
        self.zoom_scene.addItem(QGraphicsPixmapItem(QPixmap.fromImage(qimg)))
        pen = QPen(QColor(0, 255, 0), 2)
        self.zoom_scene.addRect(x_local - 1, y_local - 1, 3, 3, pen)

        q, psi = self._calculate_q_and_psi(x_glob, y_glob)
        self.current_q, self.current_psi = q, math.degrees(psi)
        self.current_x, self.current_y = x_glob, y_glob
        self.zoom_info.setText(
            f"选定点: ({x_glob}, {y_glob})  强度: {intensity:.2f}\n点击'记录当前点'保存"
        )
        self._update_integration()

    # ================================================================== #
    #  Zoom view                                                           #
    # ================================================================== #

    def _show_zoom_view(self, x: int, y: int) -> None:
        if self.display_image is None:
            return
        h, w = self.display_image.shape
        half = self.zoom_size // 2
        x1 = max(0, x - half); y1 = max(0, y - half)
        x2 = min(w, x + half); y2 = min(h, y + half)

        zone = self.display_image[y1:y2, x1:x2]
        self.zoom_scene.clear()
        qimg = ImageProcessor.apply_colormap(
            zone, self.current_colormap,
            self.contrast_min, self.contrast_max, self.contrast_mode
        )
        self.zoom_scene.addItem(QGraphicsPixmapItem(QPixmap.fromImage(qimg)))

        max_val = np.max(zone)
        my, mx = np.unravel_index(np.argmax(zone), zone.shape)
        gx, gy = x1 + mx, y1 + my

        pen = QPen(QColor(255, 0, 0), 2)
        self.zoom_scene.addRect(mx - 1, my - 1, 3, 3, pen)

        self.current_zoom_point = {
            "x": gx, "y": gy,
            "intensity": self.original_image[gy, gx],
        }

        q, psi = self._calculate_q_and_psi(gx, gy)
        self.current_q, self.current_psi = q, math.degrees(psi)
        self.current_x, self.current_y = gx, gy

        self.zoom_info.setText(
            f"放大区域: {self.zoom_size}×{self.zoom_size} px  中心: ({x}, {y})\n"
            f"最大点: ({gx}, {gy})  强度: {self.current_zoom_point['intensity']:.2f}\n"
            f"点击图像选择其他点"
        )
        self._update_integration()
        self.record_btn.setEnabled(True)

    # ================================================================== #
    #  Physics / q calculation                                             #
    # ================================================================== #

    def _calculate_q_and_psi(self, x: int, y: int) -> tuple[float, float]:
        """Return (q [Å⁻¹], ψ [rad]) for detector pixel (x, y)."""
        try:
            wavelength = float(self.wavelength_edit.text())
            px = float(self.pixel_size_x_edit.text())
            py = float(self.pixel_size_y_edit.text())
            cx = float(self.center_x_edit.text())
            cy = float(self.center_y_edit.text())
            dist = float(self.distance_edit.text())

            dx = (x - cx) * (px / 1000.0)   # mm
            dy = (y - cy) * (py / 1000.0)   # mm
            r = math.sqrt(dx**2 + dy**2)
            theta = math.atan(r / dist) / 2.0
            q = (4 * math.pi * math.sin(theta)) / wavelength
            psi = math.atan2(dy, dx)
            return q, psi
        except Exception as exc:
            QMessageBox.warning(self, "计算错误", f"无法计算 q 值:\n{exc}")
            return 0.0, 0.0

    def _setup_ai(self) -> None:
        """Initialise a pyFAI AzimuthalIntegrator from current UI values."""
        if not _PYFAI_OK:
            QMessageBox.warning(self, "错误", "未安装 pyFAI，无法进行积分")
            return
        try:
            wavelength = float(self.wavelength_edit.text()) * 1e-10
            px = float(self.pixel_size_x_edit.text()) * 1e-6
            py = float(self.pixel_size_y_edit.text()) * 1e-6
            cx = float(self.center_x_edit.text())
            cy = float(self.center_y_edit.text())
            dist = float(self.distance_edit.text()) * 1e-3

            det = pyFAI.detectors.Detector(pixel1=py, pixel2=px)
            self.ai = pyFAI.AzimuthalIntegrator(detector=det, wavelength=wavelength)
            self.ai.set_dist(dist)
            self.ai.set_poni1(cy * py)
            self.ai.set_poni2(cx * px)
            self.ai.set_rot1(0); self.ai.set_rot2(0); self.ai.set_rot3(0)
        except Exception as exc:
            QMessageBox.critical(self, "AI 初始化错误", f"创建 AzimuthalIntegrator 时出错:\n{exc}")
            traceback.print_exc()

    # ================================================================== #
    #  Integration                                                         #
    # ================================================================== #

    def _update_integration(self) -> None:
        if self.current_q is None or self.current_psi is None:
            return
        if not _PYFAI_OK or self.original_image is None:
            return
        self._setup_ai()
        if self.ai is None:
            return

        az_half = self.azimuth_range_spin.value()
        r_half  = self.radial_range_spin.value()
        npt     = self.npt_spin.value()
        npt_rad = self.npt_rad_spin.value()

        az_half_r = self.azimuth_range_spin_r.value()
        r_half_r  = self.radial_range_spin_r.value()
        npt_r     = self.npt_spin_r.value()
        npt_rad_r = self.npt_rad_spin_r.value()

        psi = self.current_psi
        q   = self.current_q

        az_range   = (psi - az_half,  psi + az_half)
        r_range    = (max(0.001, q - r_half), q + r_half)
        az_range_r = (psi - az_half_r, psi + az_half_r)
        r_range_r  = (max(0.001, q - r_half_r), q + r_half_r)

        data = self.original_image
        mask = np.where(
            (data >= self.threshold_min) & (data <= self.threshold_max), 0, 1
        )

        try:
            res_q = self.ai.integrate1d_ng(
                data, npt, unit="q_A^-1", method="splitpixel",
                correctSolidAngle=False, azimuth_range=az_range,
                radial_range=r_range, mask=mask,
            )
            _, res_psi = self.ai.integrate_radial(
                data, npt_rad=npt_rad_r, npt=npt_r,
                radial_range=r_range_r, azimuth_range=az_range_r,
                unit="chi_deg", radial_unit="q_A^-1", method="splitpixel",
                correctSolidAngle=False, mask=mask,
            )
            self._plot_integration_curves(
                res_q.radial, res_q.intensity,
                np.linspace(*az_range_r, npt_r), res_psi,
                q, psi,
            )
        except Exception as exc:
            print(f"[Integration] {exc}")
            traceback.print_exc()

    def _plot_integration_curves(self, q, i_q, psi, i_psi, q_ref, psi_ref) -> None:
        self.integration_figure.clear()
        ax1 = self.integration_figure.add_subplot(211)
        ax2 = self.integration_figure.add_subplot(212)
        self.integration_figure.subplots_adjust(hspace=0.5)

        ax1.plot(q, i_q, "b-")
        ax1.axvline(q_ref, color="r", linestyle="--", alpha=0.5, label="Original")
        if self.selected_q is not None:
            ax1.axvline(self.selected_q, color="g", linestyle="-", lw=2, label="Selected")
        ax1.set_xlabel(r"q ($\AA^{-1}$)")
        ax1.set_ylabel("Intensity")
        ax1.set_title(f"Radial Integration (Q profile) around ψ={psi_ref:.1f}°")
        ax1.legend(); ax1.grid(True)

        ax2.plot(psi, i_psi, "g-")
        ax2.axvline(psi_ref, color="r", linestyle="--", alpha=0.5, label="Original")
        if self.selected_psi is not None:
            ax2.axvline(self.selected_psi, color="g", linestyle="-", lw=2, label="Selected")
        ax2.set_xlabel(r"$\psi$ (degrees)")
        ax2.set_ylabel("Intensity")
        ax2.set_title(f"Azimuthal Integration (ψ profile) around q={q_ref:.3f} Å⁻¹")
        ax2.legend(); ax2.grid(True)

        self.integration_canvas.mpl_connect("button_press_event", self._on_curve_click)
        self.integration_canvas.draw()

    def _on_curve_click(self, event) -> None:
        if event.inaxes is None:
            return
        idx = self.integration_figure.axes.index(event.inaxes)
        if idx == 0:
            self.selected_q = event.xdata
        elif idx == 1:
            self.selected_psi = event.xdata
        self._update_integration()

    def _calculate_new_pixel(self) -> None:
        q_target   = self.selected_q   if self.selected_q   is not None else self.current_q
        psi_target = self.selected_psi if self.selected_psi is not None else self.current_psi

        if q_target is None or psi_target is None:
            return
        if self.original_image is None:
            QMessageBox.warning(self, "计算错误", "尚未加载原始图像")
            return
        try:
            wavelength = float(self.wavelength_edit.text())
            px = float(self.pixel_size_x_edit.text())
            py = float(self.pixel_size_y_edit.text())
            cx = float(self.center_x_edit.text())
            cy = float(self.center_y_edit.text())
            dist = float(self.distance_edit.text())

            sin_th = (q_target * wavelength) / (4 * math.pi)
            if abs(sin_th) > 1:
                QMessageBox.warning(self, "计算错误", "q 值超出有效范围")
                return
            theta = math.asin(sin_th)
            r_mm = dist * math.tan(2 * theta)
            psi_rad = math.radians(psi_target)
            dx_mm = r_mm * math.cos(psi_rad)
            dy_mm = r_mm * math.sin(psi_rad)
            nx = int(round(cx + (dx_mm * 1000) / px))
            ny = int(round(cy + (dy_mm * 1000) / py))

            if ny < 0 or nx < 0 or ny >= self.original_image.shape[0] or nx >= self.original_image.shape[1]:
                QMessageBox.warning(self, "计算错误", "计算得到的像素位置超出图像范围")
                return

            intensity = self.original_image[ny, nx]
            self.current_zoom_point = {"x": nx, "y": ny, "intensity": intensity}
            self._record_current_point()
            self.selected_q = None
            self.selected_psi = None
        except Exception as exc:
            QMessageBox.critical(self, "计算错误", f"计算新像素位置时出错:\n{exc}")
            traceback.print_exc()

    # ================================================================== #
    #  Record management                                                   #
    # ================================================================== #

    def _record_current_point(self) -> None:
        if self.current_zoom_point is None:
            return
        pt = self.current_zoom_point.copy()
        q, psi = self._calculate_q_and_psi(pt["x"], pt["y"])
        pt["q"] = q
        pt["psi"] = psi
        self.recorded_points.append(pt)
        self._update_record_list()
        self._draw_point_on_main_image(pt["x"], pt["y"])

    def _draw_point_on_main_image(self, x: int, y: int) -> None:
        if self.display_image is None:
            return
        pen = QPen(QColor(255, 0, 0), 3)
        rect = QGraphicsRectItem(x - 2, y - 2, 5, 5)
        rect.setPen(pen)
        self.main_scene.addItem(rect)

    def _update_record_list(self) -> None:
        self.record_list.clear()
        for i, pt in enumerate(self.recorded_points):
            q_str   = f"{pt['q']:.4f}"      if "q"   in pt else "N/A"
            psi_str = f"{math.degrees(pt['psi']):.2f}°" if "psi" in pt else "N/A"
            text = (
                f"点 {i+1}: 位置 ({pt['x']}, {pt['y']}),  强度: {pt['intensity']:.2f}\n"
                f"q = {q_str} Å⁻¹,  方位角: {psi_str}"
            )
            self.record_list.addItem(QListWidgetItem(text))

    def _delete_selected_record(self) -> None:
        selected = self.record_list.selectedItems()
        if not selected:
            return
        idxs = sorted(
            [self.record_list.row(item) for item in selected], reverse=True
        )
        for idx in idxs:
            if 0 <= idx < len(self.recorded_points):
                del self.recorded_points[idx]
        self._update_record_list()
        self._display_main_image()

    def _clear_all_records(self) -> None:
        reply = QMessageBox.question(
            self, "清空记录", "确定要清空所有记录点吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.recorded_points.clear()
            self._update_record_list()
            self._display_main_image()
