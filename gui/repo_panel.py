"""Left sidebar panel — shows the authenticated user's repository list."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .workers import FetchReposWorker

_MONITOR_INDICATOR = "  🟢"
_REPO_ROLE = Qt.ItemDataRole.UserRole
_PRIVATE_ROLE = Qt.ItemDataRole.UserRole + 1


class RepoPanel(QWidget):
    """Left panel that lists all repos owned by the current user."""

    repo_selected = Signal(str)   # emits "owner/repo" when user clicks a row
    refresh_requested = Signal()  # emits when user clicks Refresh

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("repo_panel")
        self.setMinimumWidth(220)
        self.setMaximumWidth(320)

        self._monitored_repos: set[str] = set()
        self._all_items: list[QListWidgetItem] = []   # for search filtering

        self._spin_timer = QTimer(self)
        self._spin_timer.timeout.connect(self._update_spinner)
        self._spin_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spin_idx = 0

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # ---- Header bar -------------------------------------------
        header = QWidget()
        header.setObjectName("header_widget")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 12, 12, 8)
        header_layout.setSpacing(8)

        title = QLabel("Repositories")
        title.setObjectName("panel_title")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._refresh_btn = QPushButton("⟳")
        self._refresh_btn.setFixedSize(32, 32)
        self._refresh_btn.setToolTip("Refresh repository list")
        self._refresh_btn.clicked.connect(self.refresh_requested)
        header_layout.addWidget(self._refresh_btn)

        layout.addWidget(header)

        # ---- Search box -------------------------------------------
        search_container = QWidget()
        search_container.setObjectName("search_container")
        search_layout = QVBoxLayout(search_container)
        search_layout.setContentsMargins(12, 0, 12, 8)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("🔍  Filter repos…")
        self._search_edit.textChanged.connect(self._filter_repos)
        search_layout.addWidget(self._search_edit)
        layout.addWidget(search_container)

        # ---- Repo count label -------------------------------------------
        self._count_label = QLabel("")
        self._count_label.setObjectName("section_label")
        self._count_label.setContentsMargins(18, 0, 0, 4)
        layout.addWidget(self._count_label)

        # ---- Loading label -------------------------------------------
        self._loading_label = QLabel("  Loading…")
        self._loading_label.setStyleSheet("color: #6c7086; font-size: 12px; padding: 8px;")
        self._loading_label.setVisible(False)
        layout.addWidget(self._loading_label)

        # ---- Repo list -------------------------------------------
        self._list = QListWidget()
        self._list.setObjectName("repo_list")
        self._list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._list.currentItemChanged.connect(self._on_item_changed)
        layout.addWidget(self._list, stretch=1)

    # ------------------------------------------------------------------  Public
    def set_loading(self, loading: bool) -> None:
        self._refresh_btn.setEnabled(not loading)
        self._loading_label.setVisible(loading)
        if loading:
            self._list.setVisible(False)
            self._count_label.setText("")
            self._spin_idx = 0
            self._spin_timer.start(100)
        else:
            self._list.setVisible(True)
            self._spin_timer.stop()
            self._refresh_btn.setText("⟳")

    def _update_spinner(self) -> None:
        self._refresh_btn.setText(self._spin_chars[self._spin_idx])
        self._spin_idx = (self._spin_idx + 1) % len(self._spin_chars)

    def populate(self, repos: list[dict]) -> None:
        self._list.clear()
        self._all_items.clear()

        for repo in repos:
            full_name: str = repo["full_name"]
            private: bool = repo.get("private", False)
            language: str = repo.get("language") or ""

            display = full_name
            if full_name in self._monitored_repos:
                display += _MONITOR_INDICATOR

            item = QListWidgetItem(display)
            item.setData(_REPO_ROLE, full_name)
            item.setData(_PRIVATE_ROLE, private)
            tooltip_parts = [full_name]
            if private:
                tooltip_parts.append("🔒 Private")
            if language:
                tooltip_parts.append(f"Lang: {language}")
            if repo.get("description"):
                tooltip_parts.append(repo["description"])
            item.setToolTip("\n".join(tooltip_parts))
            self._list.addItem(item)
            self._all_items.append(item)

        self._update_count()
        self._apply_search_filter(self._search_edit.text())

    def mark_monitored(self, repo: str, active: bool) -> None:
        """Add or remove the green dot indicator from a repo item."""
        if active:
            self._monitored_repos.add(repo)
        else:
            self._monitored_repos.discard(repo)

        for i in range(self._list.count()):
            item = self._list.item(i)
            full_name = item.data(_REPO_ROLE)
            if full_name == repo:
                base_text = full_name
                if full_name in self._monitored_repos:
                    base_text += _MONITOR_INDICATOR
                item.setText(base_text)
                break

    def select_repo(self, repo: str) -> None:
        """Programmatically select a repo by name (used when restoring state)."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(_REPO_ROLE) == repo:
                self._list.setCurrentItem(item)
                break

    # ------------------------------------------------------------------  Private
    def _on_item_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is None:
            return
        full_name: str = current.data(_REPO_ROLE)
        if full_name:
            self.repo_selected.emit(full_name)

    def _filter_repos(self, text: str) -> None:
        self._apply_search_filter(text)
        self._update_count()

    def _apply_search_filter(self, text: str) -> None:
        query = text.strip().lower()
        for item in self._all_items:
            full_name: str = item.data(_REPO_ROLE)
            item.setHidden(bool(query and query not in full_name.lower()))

    def _update_count(self) -> None:
        visible = sum(
            1 for item in self._all_items if not item.isHidden()
        )
        total = len(self._all_items)
        if visible == total:
            self._count_label.setText(f"  {total} REPOS")
        else:
            self._count_label.setText(f"  {visible} / {total} REPOS")
