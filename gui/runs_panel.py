"""Right panel — workflow runs table with pagination, batch delete, and monitor toggle."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QFrame,
)

from .styles import STATUS_ICONS
from .workers import DeleteRunsWorker

# Table column indices
_COL_CHECK = 0
_COL_NUM = 1
_COL_NAME = 2
_COL_STATUS = 3
_COL_BRANCH = 4
_COL_EVENT = 5
_COL_CREATED = 6
_COL_DURATION = 7
_COL_ACTIONS = 8

_ACTIVE_STATUSES = {"in_progress", "queued", "waiting", "requested", "pending"}
_RUN_ID_ROLE = Qt.ItemDataRole.UserRole
_STATUS_ROLE = Qt.ItemDataRole.UserRole + 1


def _relative_time(iso: str) -> str:
    """Convert an ISO-8601 timestamp to a human-friendly relative string."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        secs = int(delta.total_seconds())
        if secs < 60:
            return f"{secs}s ago"
        if secs < 3600:
            return f"{secs // 60}m ago"
        if secs < 86400:
            return f"{secs // 3600}h ago"
        return f"{secs // 86400}d ago"
    except Exception:
        return iso[:10]


def _duration_str(created: str, updated: str, status: str) -> str:
    """Calculate run duration."""
    try:
        t0 = datetime.fromisoformat(created.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        if status in _ACTIVE_STATUSES:
            t1 = datetime.now(timezone.utc)
        secs = max(0, int((t1 - t0).total_seconds()))
        if secs < 60:
            return f"{secs}s"
        if secs < 3600:
            return f"{secs // 60}m {secs % 60}s"
        return f"{secs // 3600}h {(secs % 3600) // 60}m"
    except Exception:
        return "—"


class RunsPanel(QWidget):
    """Right panel that shows workflow runs for the selected repo."""

    # Signals emitted upward to MainWindow
    monitor_toggled = Signal(str)   # repo — request start/stop monitor
    refresh_requested = Signal(str, int, int)  # repo, page, workflow_id (0 = all)
    download_requested = Signal(str, object)  # repo, run_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo: str = ""
        self._token: str = ""
        self._current_page: int = 1
        self._total_count: int = 0
        self._per_page: int = 50
        self._selected_workflow_id: int = 0
        self._workflows: list[dict] = []
        self._is_monitored: bool = False
        self._delete_worker: DeleteRunsWorker | None = None
        self._activity_log_visible: bool = True

        self._build_ui()
        self._show_placeholder()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # === Top toolbar ===
        toolbar = QWidget()
        toolbar.setObjectName("toolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 10, 16, 10)
        toolbar_layout.setSpacing(10)

        self._repo_label = QLabel("Select a repository")
        self._repo_label.setObjectName("panel_title")
        toolbar_layout.addWidget(self._repo_label)

        toolbar_layout.addStretch()

        # Workflow filter combo
        self._workflow_combo = QComboBox()
        self._workflow_combo.setToolTip("Filter by workflow")
        self._workflow_combo.currentIndexChanged.connect(self._on_workflow_filter_changed)
        toolbar_layout.addWidget(self._workflow_combo)

        # Select/Deselect all
        self._select_all_btn = QPushButton("☑ Select All")
        self._select_all_btn.setToolTip("Select all deletable runs")
        self._select_all_btn.clicked.connect(self._select_all)
        self._select_all_btn.setEnabled(False)
        toolbar_layout.addWidget(self._select_all_btn)

        self._deselect_btn = QPushButton("☐ Deselect")
        self._deselect_btn.clicked.connect(self._deselect_all)
        self._deselect_btn.setEnabled(False)
        toolbar_layout.addWidget(self._deselect_btn)

        # Delete button
        self._delete_btn = QPushButton("🗑 Delete Selected")
        self._delete_btn.setObjectName("btn_danger")
        self._delete_btn.setToolTip("Delete selected workflow runs (not in-progress)")
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        self._delete_btn.setEnabled(False)
        toolbar_layout.addWidget(self._delete_btn)

        # Monitor toggle
        self._monitor_btn = QPushButton("👁 Start Monitor")
        self._monitor_btn.setObjectName("btn_monitor_off")
        self._monitor_btn.setToolTip("Auto-monitor and download artifacts")
        self._monitor_btn.clicked.connect(self._on_monitor_toggled)
        self._monitor_btn.setEnabled(False)
        toolbar_layout.addWidget(self._monitor_btn)

        # Refresh
        self._refresh_btn = QPushButton("🔄 Refresh")
        self._refresh_btn.clicked.connect(self._do_refresh)
        self._refresh_btn.setEnabled(False)
        toolbar_layout.addWidget(self._refresh_btn)

        layout.addWidget(toolbar)

        # === Progress bar (hidden when not deleting) ===
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(False)
        layout.addWidget(self._progress_bar)

        # === Table ===
        self._table = QTableWidget()
        self._table.setColumnCount(9)
        self._table.setHorizontalHeaderLabels(
            ["", "#", "Workflow / Run", "Status", "Branch", "Event", "Created", "Duration", "Actions"]
        )
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(False)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(0, 40)
        self._table.setColumnWidth(1, 60)
        self._table.setColumnWidth(3, 120)
        self._table.setColumnWidth(8, 240)
        self._table.verticalHeader().setDefaultSectionSize(40)

        layout.addWidget(self._table, stretch=1)

        # === Pagination bar ===
        page_bar = QWidget()
        page_bar.setObjectName("page_bar")
        page_layout = QHBoxLayout(page_bar)
        page_layout.setContentsMargins(16, 8, 16, 8)
        page_layout.setSpacing(10)

        self._prev_btn = QPushButton("← Prev")
        self._prev_btn.clicked.connect(self._prev_page)
        self._prev_btn.setEnabled(False)
        page_layout.addWidget(self._prev_btn)

        self._page_label = QLabel("")
        self._page_label.setStyleSheet("color: #a6adc8;")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_layout.addWidget(self._page_label)

        self._next_btn = QPushButton("Next →")
        self._next_btn.clicked.connect(self._next_page)
        self._next_btn.setEnabled(False)
        page_layout.addWidget(self._next_btn)

        page_layout.addStretch()

        self._total_label = QLabel("")
        self._total_label.setStyleSheet("color: #6c7086; font-size: 12px;")
        page_layout.addWidget(self._total_label)

        layout.addWidget(page_bar)

        # === Activity Log (collapsible) ===
        self._activity_frame = QFrame()
        self._activity_frame.setObjectName("activity_frame")
        activity_outer = QVBoxLayout(self._activity_frame)
        activity_outer.setContentsMargins(0, 0, 0, 0)
        activity_outer.setSpacing(0)

        act_header = QWidget()
        act_header.setObjectName("act_header")
        act_header_layout = QHBoxLayout(act_header)
        act_header_layout.setContentsMargins(16, 4, 16, 4)

        act_title = QLabel("📋  Activity Log")
        act_title.setStyleSheet(
            "font-size:11px; font-weight:600; color:#6c7086; letter-spacing:1px;"
        )
        act_header_layout.addWidget(act_title)
        act_header_layout.addStretch()

        self._toggle_log_btn = QPushButton("▼ Hide")
        self._toggle_log_btn.setFixedSize(64, 22)
        self._toggle_log_btn.setStyleSheet(
            "font-size:11px; border-radius:4px; padding:0;"
        )
        self._toggle_log_btn.clicked.connect(self._toggle_activity_log)
        act_header_layout.addWidget(self._toggle_log_btn)

        activity_outer.addWidget(act_header)

        self._activity_log = QTextEdit()
        self._activity_log.setObjectName("activity_log")
        self._activity_log.setReadOnly(True)
        self._activity_log.setFixedHeight(110)
        activity_outer.addWidget(self._activity_log)

        layout.addWidget(self._activity_frame)

    # ------------------------------------------------------------------  Public
    def set_repo(self, repo: str, token: str) -> None:
        self._repo = repo
        self._token = token
        self._current_page = 1
        self._selected_workflow_id = 0
        self._repo_label.setText(repo)
        self._select_all_btn.setEnabled(True)
        self._deselect_btn.setEnabled(True)
        self._monitor_btn.setEnabled(True)
        self._refresh_btn.setEnabled(True)
        self._workflow_combo.blockSignals(True)
        self._workflow_combo.clear()
        self._workflow_combo.addItem("All Workflows", 0)
        self._workflow_combo.blockSignals(False)

    def set_loading(self, loading: bool) -> None:
        self._refresh_btn.setEnabled(not loading)
        if loading:
            self._table.setRowCount(0)
            self._page_label.setText("Loading…")

    def set_workflows(self, workflows: list[dict]) -> None:
        self._workflows = workflows
        self._workflow_combo.blockSignals(True)
        self._workflow_combo.clear()
        self._workflow_combo.addItem("All Workflows", 0)
        for wf in workflows:
            self._workflow_combo.addItem(wf["name"], wf["id"])
        self._workflow_combo.blockSignals(False)

    def populate_runs(self, data: dict) -> None:
        self._total_count = data.get("total_count", 0)
        runs: list[dict] = data.get("workflow_runs", [])

        self._table.setRowCount(len(runs))

        for row, run in enumerate(runs):
            run_id: int = run["id"]
            status: str = run.get("status", "")
            conclusion: str = run.get("conclusion") or status
            is_active = status in _ACTIVE_STATUSES

            # Col 0 — Checkbox
            chk = QTableWidgetItem()
            if is_active:
                chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable)
                chk.setCheckState(Qt.CheckState.Unchecked)
                chk.setForeground(QColor("#45475a"))
                chk.setToolTip("Cannot delete a run that is in progress")
            else:
                chk.setFlags(
                    Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
                )
                chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(_RUN_ID_ROLE, run_id)
            chk.setData(_STATUS_ROLE, status)
            self._table.setItem(row, _COL_CHECK, chk)

            # Col 1 — Run number
            num_item = QTableWidgetItem(str(run.get("run_number", "")))
            num_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            num_item.setForeground(QColor("#a6adc8"))
            num_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(row, _COL_NUM, num_item)

            # Col 2 — Name / display title
            name = run.get("display_title") or run.get("name", "")
            wf_name = run.get("name", "")
            name_item = QTableWidgetItem(wf_name + (f"  ·  {name}" if name != wf_name else ""))
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            name_item.setToolTip(name)
            self._table.setItem(row, _COL_NAME, name_item)

            # Col 3 — Status badge (label as cell widget for color)
            badge_label = QLabel()
            icon = STATUS_ICONS.get(conclusion, "")
            badge_label.setText(f"  {icon}  {conclusion.replace('_', ' ').title()}  ")
            badge_label.setProperty("status", conclusion)
            badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setCellWidget(row, _COL_STATUS, badge_label)

            # Col 4 — Branch
            branch = run.get("head_branch", "")
            branch_item = QTableWidgetItem(branch)
            branch_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            branch_item.setForeground(QColor("#89b4fa"))
            self._table.setItem(row, _COL_BRANCH, branch_item)

            # Col 5 — Event
            event_item = QTableWidgetItem(run.get("event", ""))
            event_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            event_item.setForeground(QColor("#a6adc8"))
            self._table.setItem(row, _COL_EVENT, event_item)

            # Col 6 — Created
            created_str = run.get("created_at", "")
            created_item = QTableWidgetItem(_relative_time(created_str))
            created_item.setToolTip(created_str)
            created_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            created_item.setForeground(QColor("#6c7086"))
            self._table.setItem(row, _COL_CREATED, created_item)

            # Col 7 — Duration
            dur = _duration_str(
                run.get("created_at", ""),
                run.get("updated_at", ""),
                status,
            )
            dur_item = QTableWidgetItem(dur)
            dur_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            dur_item.setForeground(QColor("#6c7086"))
            self._table.setItem(row, _COL_DURATION, dur_item)

            # Col 8 — Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(8)

            dl_btn = QPushButton("Download")
            dl_btn.setFixedHeight(24)
            dl_btn.setMinimumWidth(100)
            dl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            dl_btn.clicked.connect(lambda checked, rid=run_id: self.download_requested.emit(self._repo, rid))

            del_btn = QPushButton("Delete")
            del_btn.setFixedHeight(24)
            del_btn.setMinimumWidth(80)
            del_btn.setObjectName("btn_danger")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda checked, rid=run_id: self._start_delete([rid]))

            if is_active:
                del_btn.setEnabled(False)
                dl_btn.setEnabled(False)

            actions_layout.addWidget(dl_btn)
            actions_layout.addWidget(del_btn)
            actions_layout.addStretch()

            self._table.setCellWidget(row, _COL_ACTIONS, actions_widget)

        # Update pagination
        total_pages = max(1, math.ceil(self._total_count / self._per_page))
        self._page_label.setText(f"Page {self._current_page} of {total_pages}")
        self._prev_btn.setEnabled(self._current_page > 1)
        self._next_btn.setEnabled(self._current_page < total_pages)
        self._total_label.setText(f"{self._total_count} total runs")
        self._delete_btn.setEnabled(self._total_count > 0)

    def set_monitored(self, active: bool) -> None:
        self._is_monitored = active
        if active:
            self._monitor_btn.setObjectName("btn_monitor_on")
            self._monitor_btn.setText("🔴 Stop Monitor")
        else:
            self._monitor_btn.setObjectName("btn_monitor_off")
            self._monitor_btn.setText("👁 Start Monitor")
        # Force stylesheet re-evaluation
        self._monitor_btn.style().unpolish(self._monitor_btn)
        self._monitor_btn.style().polish(self._monitor_btn)

    def append_log(self, message: str) -> None:
        """Append a timestamped line to the activity log."""
        ts = datetime.now().strftime("%H:%M:%S")
        self._activity_log.append(f"[{ts}]  {message}")
        # Auto-scroll to bottom
        sb = self._activity_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_run_deleted(self, run_id: int) -> None:
        """Remove a deleted run from the table immediately."""
        for row in range(self._table.rowCount()):
            item = self._table.item(row, _COL_CHECK)
            if item and item.data(_RUN_ID_ROLE) == run_id:
                self._table.removeRow(row)
                self._total_count = max(0, self._total_count - 1)
                self._total_label.setText(f"{self._total_count} total runs")
                break

    # ------------------------------------------------------------------  Private
    def _show_placeholder(self) -> None:
        self._repo_label.setText("Select a repository  →")
        self._table.setRowCount(0)
        self._page_label.setText("")
        self._total_label.setText("")

    def _select_all(self) -> None:
        for row in range(self._table.rowCount()):
            item = self._table.item(row, _COL_CHECK)
            if item and item.flags() & Qt.ItemFlag.ItemIsEnabled:
                item.setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self) -> None:
        for row in range(self._table.rowCount()):
            item = self._table.item(row, _COL_CHECK)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

    def _get_checked_run_ids(self) -> list[int]:
        ids: list[int] = []
        for row in range(self._table.rowCount()):
            item = self._table.item(row, _COL_CHECK)
            if item and item.checkState() == Qt.CheckState.Checked:
                ids.append(item.data(_RUN_ID_ROLE))
        return ids

    def _on_delete_clicked(self) -> None:
        ids = self._get_checked_run_ids()
        if not ids:
            QMessageBox.information(
                self, "Nothing selected",
                "Please check at least one workflow run to delete."
            )
            return
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {len(ids)} workflow run(s)?\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._start_delete(ids)

    def _start_delete(self, run_ids: list[int]) -> None:
        self._delete_btn.setEnabled(False)
        self._progress_bar.setMaximum(len(run_ids))
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self.append_log(f"Deleting {len(run_ids)} run(s)…")

        self._delete_worker = DeleteRunsWorker(self._repo, run_ids, self._token)
        self._delete_worker.progress.connect(self._on_delete_progress)
        self._delete_worker.run_deleted.connect(self.on_run_deleted)
        self._delete_worker.done.connect(self._on_delete_done)
        self._delete_worker.error.connect(
            lambda msg: self.append_log(f"⚠ Delete error: {msg}")
        )
        self._delete_worker.start()

    def _on_delete_progress(self, current: int, total: int) -> None:
        self._progress_bar.setValue(current)

    def _on_delete_done(self, count: int) -> None:
        self._progress_bar.setVisible(False)
        self._delete_btn.setEnabled(True)
        self.append_log(f"✅ Deleted {count} run(s) successfully.")

    def _on_monitor_toggled(self) -> None:
        if self._repo:
            self.monitor_toggled.emit(self._repo)

    def _on_workflow_filter_changed(self, index: int) -> None:
        wf_id = self._workflow_combo.itemData(index) or 0
        self._selected_workflow_id = wf_id
        self._current_page = 1
        self._do_refresh()

    def _do_refresh(self) -> None:
        if self._repo:
            self.refresh_requested.emit(
                self._repo, self._current_page, self._selected_workflow_id
            )

    def _prev_page(self) -> None:
        if self._current_page > 1:
            self._current_page -= 1
            self._do_refresh()

    def _next_page(self) -> None:
        total_pages = max(1, math.ceil(self._total_count / self._per_page))
        if self._current_page < total_pages:
            self._current_page += 1
            self._do_refresh()

    def _toggle_activity_log(self) -> None:
        self._activity_log_visible = not self._activity_log_visible
        self._activity_log.setVisible(self._activity_log_visible)
        self._toggle_log_btn.setText(
            "▼ Hide" if self._activity_log_visible else "▶ Show"
        )
