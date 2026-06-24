#!/usr/bin/env python3
"""
GitHub Actions Manager — GUI entry point.

Launch with:
    python gui_main.py
    # or, if using uv:
    uv run python gui_main.py
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from gui.config import Config
from gui.main_window import MainWindow
from gui.styles import get_stylesheet


def main() -> None:
    # High-DPI support (Qt 6 enables this by default, but explicit is safer)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("GitHub Actions Manager")
    app.setOrganizationName("github-actions-manager")
    app.setApplicationDisplayName("GitHub Actions Manager")

    # Apply dynamic theme from config
    config = Config()
    app.setStyleSheet(get_stylesheet(config.theme))

    # Preferred system font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
