"""Monitor configuration dialog — sets download dir and poll interval."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class MonitorDialog(QDialog):
    """Dialog to configure (or update) the monitor settings for a repo."""

    def __init__(
        self,
        repo: str,
        current_download_dir: str = "",
        current_interval: int = 60,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.repo = repo
        self.setWindowTitle(f"Configure Monitor — {repo}")
        self.setMinimumWidth(500)
        self.setModal(True)

        self._build_ui(current_download_dir, current_interval)

    # ------------------------------------------------------------------
    def _build_ui(self, download_dir: str, interval: int) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel(f"Auto-Monitor  ·  {self.repo}")
        title.setObjectName("panel_title")
        root.addWidget(title)

        description = QLabel(
            "When a new <b>successful</b> workflow run is detected, its "
            "artifacts will be downloaded automatically to the chosen directory."
        )
        description.setWordWrap(True)
        description.setProperty("color", "sub")
        root.addWidget(description)

        # Form
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Download directory
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        default_dir = str(Path.home() / "Downloads" / "github-artifacts")
        self._dir_edit = QLineEdit(download_dir or default_dir)
        self._dir_edit.setPlaceholderText("Select download directory…")
        dir_row.addWidget(self._dir_edit)

        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_dir)
        dir_row.addWidget(browse_btn)
        form.addRow("Download directory:", dir_row)

        # Poll interval
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(10, 3600)
        self._interval_spin.setValue(interval)
        self._interval_spin.setSuffix("  seconds")
        self._interval_spin.setToolTip(
            "How often (in seconds) to poll GitHub for new workflow runs."
        )
        form.addRow("Poll interval:", self._interval_spin)

        root.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("btn_primary")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Start Monitoring")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------
    def _browse_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Select Download Directory", self._dir_edit.text()
        )
        if directory:
            self._dir_edit.setText(directory)

    # --- Accessors used by the caller ---------------------------------
    @property
    def download_dir(self) -> str:
        return self._dir_edit.text().strip()

    @property
    def poll_interval(self) -> int:
        return self._interval_spin.value()
