"""Left sidebar panel — shows the authenticated user's repository list."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
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
    star_toggled = Signal(str, bool)  # emits "owner/repo", is_starred

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("repo_panel")
        self.setMinimumWidth(220)
        self.setMaximumWidth(320)

        self._monitored_repos: set[str] = set()
        self._starred_repos: set[str] = set()
        self._all_items: list[QListWidgetItem] = []   # for search filtering
        self._last_repos_data: list[dict] = []

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

        self._refresh_btn = QPushButton("🔄")
        self._refresh_btn.setFixedSize(32, 32)
        self._refresh_btn.setStyleSheet("padding: 0;")
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
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._list, stretch=1)

    # ------------------------------------------------------------------  Public
    def set_loading(self, loading: bool) -> None:
        self._refresh_btn.setEnabled(not loading)
        self._loading_label.setVisible(loading and self._list.count() == 0)
        if loading:
            if self._list.count() == 0:
                self._list.setVisible(False)
                self._count_label.setText("")
            self._spin_idx = 0
            self._spin_timer.start(100)
        else:
            self._list.setVisible(True)
            self._spin_timer.stop()
            self._refresh_btn.setText("🔄")

    def _update_spinner(self) -> None:
        self._refresh_btn.setText(self._spin_chars[self._spin_idx])
        self._spin_idx = (self._spin_idx + 1) % len(self._spin_chars)

    def set_starred_repos(self, repos: set[str]) -> None:
        self._starred_repos = set(repos)

    def populate(self, repos: list[dict]) -> None:
        self._last_repos_data = repos
        self._list.clear()
        self._all_items.clear()

        def sort_key(r: dict) -> tuple[int, str]:
            full_name = r.get("full_name", "")
            return (0 if full_name in self._starred_repos else 1, full_name.lower())

        repos = sorted(repos, key=sort_key)

        for repo in repos:
            full_name: str = repo["full_name"]
            private: bool = repo.get("private", False)
            language: str = repo.get("language") or ""

            display = full_name
            if full_name in self._starred_repos:
                display = "⭐ " + display
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
                if full_name in self._starred_repos:
                    base_text = "⭐ " + base_text
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
    def _show_context_menu(self, pos: QPoint) -> None:
        item = self._list.itemAt(pos)
        if not item:
            return
        full_name = item.data(_REPO_ROLE)
        menu = QMenu(self)

        is_starred = full_name in self._starred_repos
        action_text = "Unstar" if is_starred else "Star"
        star_action = menu.addAction(f"{action_text} Repository")

        action = menu.exec(self._list.mapToGlobal(pos))
        if action == star_action:
            if is_starred:
                self._starred_repos.discard(full_name)
            else:
                self._starred_repos.add(full_name)
            self.star_toggled.emit(full_name, not is_starred)

            selected = self._list.currentItem()
            selected_name = selected.data(_REPO_ROLE) if selected else None

            if self._last_repos_data:
                self._list.blockSignals(True)
                self.populate(self._last_repos_data)
                if selected_name:
                    self.select_repo(selected_name)
                self._list.blockSignals(False)

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
