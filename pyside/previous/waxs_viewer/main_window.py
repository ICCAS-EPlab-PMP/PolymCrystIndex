"""
main_window.py  –  主窗口，将原始图像分析与积分图像寻峰合并为双 Tab 界面。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QPalette, QColor
from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout

from .raw_image_tab import RawImageTab
from .integrated_tab import IntegratedTab
from .styles import AppStyles


class MainWindow(QMainWindow):
    """Top-level application window.

    Contains a ``QTabWidget`` with two tabs:

    * **原始图像分析** – raw detector image peak picker (``RawImageTab``)
    * **积分图像寻峰** – 2D integrated data peak finder (``IntegratedTab``)
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WAXS 衍射数据分析工具")
        self.setGeometry(0, 0, 1600, 1000)

        # Window background
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#edf2ff"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # Status bar
        sb = self.statusBar()
        sb.setStyleSheet(AppStyles.STATUS_BAR)

        # ── Central widget ────────────────────────────────────────────
        central = QWidget()
        root_lay = QVBoxLayout(central)
        root_lay.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(central)

        # ── Outer tab widget (two main modes) ─────────────────────────
        self.mode_tabs = QTabWidget()
        self.mode_tabs.setStyleSheet(AppStyles.TAB_WIDGET)
        root_lay.addWidget(self.mode_tabs)

        self.raw_tab        = RawImageTab(status_bar=sb)
        self.integrated_tab = IntegratedTab(status_bar=sb)

        self.mode_tabs.addTab(self.raw_tab,        "📷  原始图像分析")
        self.mode_tabs.addTab(self.integrated_tab, "📊  积分图像寻峰")

        # ── Menus ──────────────────────────────────────────────────────
        self._build_menus()

        self.showMaximized()

    # ================================================================== #
    #  Menu bar                                                            #
    # ================================================================== #

    def _build_menus(self) -> None:
        mb = self.menuBar()

        # ── File ───────────────────────────────────────────────────────
        file_menu = mb.addMenu("文件")

        # Raw image sub-section
        open_raw = QAction("打开衍射图像 (EDF/TIFF)…", self)
        open_raw.triggered.connect(self._open_raw)
        file_menu.addAction(open_raw)

        open_poni = QAction("导入 PONI 标定文件…", self)
        open_poni.triggered.connect(self._open_poni)
        file_menu.addAction(open_poni)

        export_raw = QAction("导出原始图像记录点…", self)
        export_raw.triggered.connect(self._export_raw)
        file_menu.addAction(export_raw)

        file_menu.addSeparator()

        # Integrated sub-section
        open_int = QAction("打开 2D 积分数据 (NPY/TIFF)…", self)
        open_int.triggered.connect(self._open_integrated)
        file_menu.addAction(open_int)

        open_info = QAction("导入坐标信息文件 (TXT)…", self)
        open_info.triggered.connect(self._open_info)
        file_menu.addAction(open_info)

        open_miller = QAction("导入米勒指数文件…", self)
        open_miller.triggered.connect(self._open_miller)
        file_menu.addAction(open_miller)

        export_int = QAction("导出积分寻峰记录…", self)
        export_int.triggered.connect(self._export_integrated)
        file_menu.addAction(export_int)

        file_menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # ── Help ───────────────────────────────────────────────────────
        help_menu = mb.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ── Menu action delegates ──────────────────────────────────────────

    def _open_raw(self)        -> None: self.raw_tab.open_file()
    def _open_poni(self)       -> None: self.raw_tab.import_poni_file()
    def _export_raw(self)      -> None: self.raw_tab.export_recorded_points()
    def _open_integrated(self) -> None: self.integrated_tab.open_file()
    def _open_info(self)       -> None: self.integrated_tab._import_info_file_manually()
    def _open_miller(self)     -> None: self.integrated_tab.import_miller_indices_file()
    def _export_integrated(self) -> None: self.integrated_tab.export_recorded_peaks()

    def _show_about(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "关于",
            "WAXS 衍射数据分析工具\n\n"
            "模式一：原始图像分析\n"
            "  • 加载 TIFF / EDF 格式原始衍射图像\n"
            "  • 设置阈值、点击峰位、pyFAI 积分精确 q / ψ\n"
            "  • 导出 CSV + 标记图像\n\n"
            "模式二：2D 积分图像寻峰\n"
            "  • 加载 q–Azimuth 积分结果 (NPY / TIFF)\n"
            "  • 精准/粗略模式，1D 切片 + 自动寻峰\n"
            "  • 米勒指数叠加显示\n"
            "  • 导出 CSV + 标记图像\n\n"
            "依赖: PySide6 · pyFAI · fabio · matplotlib · scipy\n"
            "联系: tyma507@iccas.ac.cn\n"
            "版本: 2.0"
        )
