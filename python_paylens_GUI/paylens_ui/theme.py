def ensure_fonts():
    """Qt's Windows offscreen plugin does not enumerate installed system fonts."""
    import os
    from pathlib import Path
    from PySide6.QtGui import QFontDatabase
    if os.name == "nt" and not QFontDatabase.families():
        fonts = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
        for name in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf"):
            if (fonts / name).exists():
                QFontDatabase.addApplicationFont(str(fonts / name))


THEME = """
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #24374b; }
QMainWindow, QScrollArea, QStackedWidget { background: #f2f5f8; }
QWidget#sidebar { background: #142c41; }
QWidget#sidebar QLabel { color: #c5d5e3; }
QWidget#sidebar QPushButton { background: transparent; color: #cfdeeb; text-align: left; border: 0; padding: 13px 17px; }
QWidget#sidebar QPushButton:checked { background: #24485b; color: #74e2d4; border-left: 3px solid #38c5b4; }
QLabel#brand { font-size: 26px; font-weight: 700; color: white; padding: 15px; }
QLabel#pageTitle { font-size: 25px; font-weight: 650; color: #142c41; }
QLabel#badge { color: #087f78; background: #daf3ee; padding: 7px 12px; border-radius: 5px; font-weight: 600; }
QLabel[muted="true"] { color: #617287; }
QLabel[error="true"] { color: #b64635; font-size: 11px; }
QGroupBox { background: white; border: 1px solid #dbe3eb; border-radius: 7px; margin-top: 19px; padding: 17px 12px 10px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit { background: white; border: 1px solid #ccd6e0; border-radius: 4px; padding: 6px; min-height: 20px; selection-background-color: #b5e6de; }
QComboBox { padding-right: 20px; }
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QTableView:focus, QPushButton:focus { border: 2px solid #139e92; }
QLineEdit:disabled, QComboBox:disabled { background: #edf1f5; color: #8995a2; }
QPushButton { background: white; border: 1px solid #cbd6df; border-radius: 4px; padding: 8px 11px; min-height: 18px; }
QPushButton:hover { background: #e6f4f1; border-color: #69b9af; }
QPushButton[primary="true"] { background: #078d83; color: white; border-color: #078d83; font-weight: 600; }
QPushButton:disabled { background: #e4e9ee; color: #8794a1; }
QPlainTextEdit { background: white; border: 1px solid #ccd6e0; border-radius: 5px; padding: 8px; }
QPlainTextEdit#jsonEditor { background: #142638; color: #dce8f3; border: 1px solid #203d53; selection-background-color: #376b7a; }
QTableView { background: white; alternate-background-color: #f5f8fa; border: 1px solid #dce4ec; gridline-color: #ecf0f4; selection-background-color: #c6eae4; selection-color: #183b48; }
QHeaderView::section { background: #eaf0f5; color: #43586b; padding: 7px; border: 0; border-right: 1px solid #dce4ec; font-weight: 600; }
QTabWidget::pane { border: 1px solid #dce4ec; background: white; }
QTabBar::tab { background: #e6ecf2; padding: 9px 12px; }
QTabBar::tab:selected { background: white; border-top: 2px solid #0c998d; }
QSplitter::handle { background: #e1e8ef; }
QStatusBar { background: #e9eff4; color: #50697b; }
"""
