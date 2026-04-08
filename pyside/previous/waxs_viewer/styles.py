"""
styles.py  –  Centralised QSS style constants for the WAXS Viewer.
"""


class AppStyles:
    # ------------------------------------------------------------------ #
    #  Push-button                                                         #
    # ------------------------------------------------------------------ #
    BUTTON = """
        QPushButton {
            background-color: #d0edff;
            color: #104fb9;
            border-radius: 10px;
            padding: 10px 20px;
            border: none;
            font-family: "Microsoft Yahei";
            font-weight: bold;
            font-size: 12px;
        }
        QPushButton:hover  { background-color: #7ad6fb; }
        QPushButton:pressed { background-color: #44bcf9; }
    """

    # ------------------------------------------------------------------ #
    #  Group-box (with inner labels, line-edits, buttons, combos)         #
    # ------------------------------------------------------------------ #
    GROUP = """
        QGroupBox {
            font-family: "Microsoft Yahei";
            font-weight: bold;
            font-size: 18px;
            padding-top: 30px;
            margin-top: 1.5ex;
            border: 1px solid #7ad6fb;
            border-radius: 8px;
            background-color: transparent;
        }
        QGroupBox::title {
            padding-top: 10px;
            color: #103d7e;
            subcontrol-position: top center;
        }
        QLabel {
            color: #103d7e;
            font: bold 12px "Microsoft Yahei";
        }
        QLineEdit {
            color: #103d7e;
            background-color: white;
            font: bold 12px "Arial";
            border: 1px solid #104fb9;
            border-radius: 2px;
            padding: 3px;
        }
        QPushButton {
            background-color: #d0edff;
            color: #104fb9;
            border-radius: 6px;
            padding: 8px 10px;
            border: none;
            font-family: "Microsoft Yahei";
            font-weight: bold;
            font-size: 12px;
        }
        QPushButton:hover  { background-color: #7ad6fb; }
        QPushButton:pressed { background-color: #44bcf9; }
        QComboBox {
            font: bold 14px "Microsoft Yahei";
            color: #103d7e;
            border-radius: 2px;
        }
        QComboBox QAbstractItemView {
            font: 12px "Arial";
            color: #1062ec;
            border-radius: 2px;
        }
    """

    # ------------------------------------------------------------------ #
    #  Tab widget                                                          #
    # ------------------------------------------------------------------ #
    TAB_WIDGET = """
        QTabWidget::pane {
            border: 1px solid #7096D1;
            background-color: #ebfaff;
        }
        QTabBar::tab {
            background-color: #d0edff;
            color: #103d7e;
            border: 1px solid #2499f8;
            border-top-left-radius: 20px;
            border-top-right-radius: 20px;
            padding: 8px 16px;
            margin-right: 2px;
            font-weight: bold;
        }
        QTabBar::tab:selected {
            background-color: #103d7e;
            color: #d0edff;
            border-bottom: none;
        }
        QTabBar::tab:hover {
            background-color: #1062ec;
            color: #d0edff;
        }
    """

    # ------------------------------------------------------------------ #
    #  Status bar                                                          #
    # ------------------------------------------------------------------ #
    STATUS_BAR = """
        QStatusBar {
            background-color: #ebfaff;
            color: #103d7e;
            border-top: 1px solid #7096D1;
            font-size: 12px;
        }
    """

    # ------------------------------------------------------------------ #
    #  Splitter handle                                                     #
    # ------------------------------------------------------------------ #
    SPLITTER = """
        QSplitter::handle { background-color: #ebfaff; }
    """

    # ------------------------------------------------------------------ #
    #  Main image group-box (borderless card style)                        #
    # ------------------------------------------------------------------ #
    IMAGE_GROUP = """
        QGroupBox {
            font-family: "Microsoft Yahei";
            font-weight: bold;
            font-size: 16px;
            padding-top: 15px;
            margin-top: 1.5ex;
            border: none;
            background-color: #F9FCFF;
            border-radius: 15px;
        }
        QGroupBox::title {
            padding-left: 5px;
            color: #103d7e;
            subcontrol-position: top center;
        }
    """

    # ------------------------------------------------------------------ #
    #  Contrast / settings group-box (dashed border)                      #
    # ------------------------------------------------------------------ #
    SETTINGS_GROUP = """
        QGroupBox {
            font-family: "Microsoft Yahei";
            font-weight: bold;
            font-size: 14px;
            padding-top: 15px;
            margin-top: 1.5ex;
            border: 1px dashed #2499f8;
            background-color: #F9FCFF;
            border-radius: 8px;
        }
        QGroupBox::title {
            padding-left: 5px;
            color: #103d7e;
            subcontrol-position: top center;
        }
        QLabel {
            color: #103d7e;
            font: bold 12px "Microsoft Yahei";
        }
        QComboBox {
            font: bold 14px "Microsoft Yahei";
            color: #103d7e;
            border-radius: 2px;
        }
        QComboBox QAbstractItemView {
            font: 12px "Arial";
            color: #1062ec;
            border-radius: 2px;
        }
    """

    # ------------------------------------------------------------------ #
    #  Info / about group-box (semi-transparent)                          #
    # ------------------------------------------------------------------ #
    INFO_GROUP = """
        QGroupBox {
            font-family: "Microsoft Yahei";
            font-weight: bold;
            font-size: 12px;
            padding-top: 0px;
            margin-top: 1.5ex;
            border: 1px solid #7ad6fb;
            border-radius: 8px;
            background-color: rgba(235, 242, 255, 0.3);
        }
    """
