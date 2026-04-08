#!/usr/bin/env python3
"""
main.py  –  WAXS 衍射数据分析工具入口。

Usage:
    python main.py
"""

import sys

import matplotlib
from PySide6.QtWidgets import QApplication

from waxs_viewer.main_window import MainWindow


matplotlib.use("QtAgg")


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("WAXS 衍射数据分析工具")
    app.setOrganizationName("ICCAS Engineering Plastics Lab")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
