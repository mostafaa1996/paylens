"""Run with: python python_paylens_GUI/main.py"""
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from paylens_ui.window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PayLens Simulator")
    app.setLayoutDirection(Qt.LeftToRight)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
