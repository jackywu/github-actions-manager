"""Token settings dialog — validates the token and shows the authenticated user."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from .config import Config
from .workers import FetchUserWorker


class SettingsDialog(QDialog):
    """Modal dialog for entering and validating a GitHub personal access token."""

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self._worker: FetchUserWorker | None = None

        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self.setModal(True)

        self._build_ui()
        self._load_existing_settings()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 24)

        # --- Title ---
        title = QLabel("GitHub Personal Access Token")
        title.setObjectName("panel_title")
        root.addWidget(title)

        hint = QLabel(
            "Generate a token at <a href='https://github.com/settings/tokens'>"
            "github.com/settings/tokens</a> with <b>repo</b> and "
            "<b>workflow</b> scopes."
        )
        hint.setOpenExternalLinks(True)
        hint.setWordWrap(True)
        hint.setProperty("color", "sub")
        root.addWidget(hint)

        # --- Token input row ---
        token_row = QHBoxLayout()
        token_row.setSpacing(8)

        self._token_edit = QLineEdit()
        self._token_edit.setPlaceholderText("ghp_xxxxxxxxxxxxxxxxxxxx")
        self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_edit.setMinimumHeight(32)
        token_row.addWidget(self._token_edit)

        self._toggle_btn = QPushButton("Show")
        self._toggle_btn.setFixedWidth(70)
        self._toggle_btn.setMinimumHeight(32)
        self._toggle_btn.clicked.connect(self._toggle_visibility)
        token_row.addWidget(self._toggle_btn)

        root.addLayout(token_row)

        # --- Validate button + status label ---
        validate_row = QHBoxLayout()
        validate_row.setSpacing(12)

        self._validate_btn = QPushButton("Validate Token")
        self._validate_btn.setObjectName("btn_primary")
        self._validate_btn.setMinimumHeight(32)
        self._validate_btn.clicked.connect(self._validate_token)
        validate_row.addWidget(self._validate_btn)

        self._status_label = QLabel("")
        self._status_label.setProperty("color", "sub")
        validate_row.addWidget(self._status_label, stretch=1)

        root.addLayout(validate_row)

        # --- User info chip (hidden until validated) ---
        self._user_widget = QWidget()
        user_layout = QHBoxLayout(self._user_widget)
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_layout.setSpacing(8)

        self._avatar_label = QLabel("👤")
        self._avatar_label.setStyleSheet("font-size: 24px;")
        user_layout.addWidget(self._avatar_label)

        user_info_col = QVBoxLayout()
        self._username_label = QLabel("")
        self._username_label.setProperty("color", "primary")
        self._name_label = QLabel("")
        self._name_label.setProperty("color", "sub")
        user_info_col.addWidget(self._username_label)
        user_info_col.addWidget(self._name_label)
        user_layout.addLayout(user_info_col)
        user_layout.addStretch()

        self._user_widget.setVisible(False)
        root.addWidget(self._user_widget)

        # --- Workspace input row ---
        workspace_label = QLabel("Workspace Directory")
        workspace_label.setObjectName("panel_title")
        root.addWidget(workspace_label)

        ws_hint = QLabel(
            "Downloads will be organized by repository inside this directory."
        )
        ws_hint.setProperty("color", "sub")
        root.addWidget(ws_hint)

        ws_row = QHBoxLayout()
        ws_row.setSpacing(8)

        self._workspace_edit = QLineEdit()
        self._workspace_edit.setPlaceholderText("Select workspace directory…")
        self._workspace_edit.setMinimumHeight(32)
        ws_row.addWidget(self._workspace_edit)

        self._ws_browse_btn = QPushButton("Browse…")
        self._ws_browse_btn.setFixedWidth(100)
        self._ws_browse_btn.setMinimumHeight(32)
        self._ws_browse_btn.clicked.connect(self._browse_workspace)
        ws_row.addWidget(self._ws_browse_btn)

        root.addLayout(ws_row)

        # --- Dialog buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_existing_settings(self) -> None:
        if self.config.token:
            self._token_edit.setText(self.config.token)
        if self.config.workspace:
            self._workspace_edit.setText(self.config.workspace)

    def _browse_workspace(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Select Workspace Directory", self._workspace_edit.text()
        )
        if directory:
            self._workspace_edit.setText(directory)

    # ------------------------------------------------------------------
    def _toggle_visibility(self) -> None:
        if self._token_edit.echoMode() == QLineEdit.EchoMode.Password:
            self._token_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self._toggle_btn.setText("Hide")
        else:
            self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self._toggle_btn.setText("Show")

    def _validate_token(self) -> None:
        token = self._token_edit.text().strip()
        if not token:
            self._status_label.setText("⚠ Please enter a token first.")
            return

        self._validate_btn.setEnabled(False)
        self._validate_btn.setText("Validating…")
        self._status_label.setText("")
        self._user_widget.setVisible(False)

        self._worker = FetchUserWorker(token)
        self._worker.user_fetched.connect(self._on_user_fetched)
        self._worker.error.connect(self._on_validate_error)
        self._worker.start()

    def _on_user_fetched(self, user: dict) -> None:
        self._validate_btn.setEnabled(True)
        self._validate_btn.setText("Validate Token")
        self._status_label.setText("✅ Token is valid")
        self._status_label.setProperty("color", "success")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

        login = user.get("login", "")
        name = user.get("name") or login
        self._username_label.setText(f"@{login}")
        self._name_label.setText(name)
        self._user_widget.setVisible(True)

    def _on_validate_error(self, msg: str) -> None:
        self._validate_btn.setEnabled(True)
        self._validate_btn.setText("Validate Token")
        self._status_label.setText(f"❌ {msg}")
        self._status_label.setProperty("color", "danger")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def _save_and_accept(self) -> None:
        token = self._token_edit.text().strip()
        workspace = self._workspace_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "Missing Token", "Please enter a GitHub token.")
            return
        if not workspace:
            QMessageBox.warning(self, "Missing Workspace", "Please select a workspace directory.")
            return
        self.config.token = token
        self.config.workspace = workspace
        self.accept()
