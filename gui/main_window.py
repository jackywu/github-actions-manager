"""Main application window — orchestrates all panels and background workers."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QWidget,
)

from .config import Config
from .monitor_dialog import MonitorDialog
from .repo_panel import RepoPanel
from .runs_panel import RunsPanel
from .settings_dialog import SettingsDialog
from .styles import get_stylesheet
from .workers import FetchReposWorker, FetchRunsWorker, MonitorWorker


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GitHub Actions Manager")
        self.setMinimumSize(1100, 680)

        self.config = Config()

        # Active monitor workers keyed by "owner/repo"
        self._monitors: dict[str, MonitorWorker] = {}

        # Background workers (kept alive while running)
        self._fetch_repos_worker: FetchReposWorker | None = None
        self._fetch_runs_worker: FetchRunsWorker | None = None

        self._current_repo: str = ""

        self._build_ui()
        self._build_menus()

        # Auto-load repos if token is already set; otherwise open settings
        if self.config.token:
            if self.config.cached_repos:
                self._repo_panel.populate(self.config.cached_repos)
            self._restore_monitors()
            self._load_repos()
        else:
            self._open_settings()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        self._repo_panel = RepoPanel()
        self._runs_panel = RunsPanel()

        splitter.addWidget(self._repo_panel)
        splitter.addWidget(self._runs_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 840])

        self.setCentralWidget(splitter)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._update_status()

        # Wire signals
        self._repo_panel.repo_selected.connect(self._on_repo_selected)
        self._repo_panel.refresh_requested.connect(self._load_repos)
        self._runs_panel.monitor_toggled.connect(self._toggle_monitor)
        self._runs_panel.refresh_requested.connect(self._load_runs)

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        settings_action = QAction("⚙ Settings…", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # View menu
        view_menu = menu_bar.addMenu("View")

        refresh_repos_action = QAction("⟳ Refresh Repos", self)
        refresh_repos_action.setShortcut("Ctrl+R")
        refresh_repos_action.triggered.connect(self._load_repos)
        view_menu.addAction(refresh_repos_action)

        view_menu.addSeparator()

        toggle_theme_action = QAction("🌓 Toggle Light/Dark Theme", self)
        toggle_theme_action.setShortcut("Ctrl+T")
        toggle_theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(toggle_theme_action)

    # ----------------------------------------------------------------  Theme
    def _toggle_theme(self) -> None:
        if self.config.theme == "light":
            self.config.theme = "dark"
        else:
            self.config.theme = "light"
        self._apply_theme()

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_stylesheet(self.config.theme))

    # ----------------------------------------------------------------  Actions
    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self._update_status()
            self._load_repos()

    def _load_repos(self) -> None:
        if not self.config.token:
            return
        self._repo_panel.set_loading(True)
        self._status_bar.showMessage("Fetching repositories…")

        self._fetch_repos_worker = FetchReposWorker(self.config.token)
        self._fetch_repos_worker.repos_fetched.connect(self._on_repos_fetched)
        self._fetch_repos_worker.error.connect(self._on_fetch_repos_error)
        self._fetch_repos_worker.start()

    def _on_repos_fetched(self, repos: list[dict]) -> None:
        self._repo_panel.set_loading(False)
        self.config.cached_repos = repos
        self._repo_panel.populate(repos)
        # Refresh monitor indicators
        for repo in self._monitors:
            self._repo_panel.mark_monitored(repo, True)
        self._status_bar.showMessage(
            f"Loaded {len(repos)} repositories", 4000
        )

    def _on_fetch_repos_error(self, msg: str) -> None:
        self._repo_panel.set_loading(False)
        self._status_bar.showMessage(f"Error fetching repos: {msg}", 6000)
        if "401" in msg or "Unauthorized" in msg.lower():
            QMessageBox.warning(
                self, "Authentication Failed",
                "The GitHub token is invalid or expired.\n"
                "Please update it in File → Token Settings."
            )

    # ----------------------------------------------------------------  Runs
    def _on_repo_selected(self, repo: str) -> None:
        self._current_repo = repo
        is_monitored = repo in self._monitors
        self._runs_panel.set_repo(repo, self.config.token)
        self._runs_panel.set_monitored(is_monitored)
        self._load_runs(repo, 1, 0)

    def _load_runs(self, repo: str, page: int, workflow_id: int) -> None:
        if not repo or not self.config.token:
            return
        self._runs_panel.set_loading(True)
        self._status_bar.showMessage(f"Loading runs for {repo}…")

        self._fetch_runs_worker = FetchRunsWorker(
            repo, self.config.token,
            page=page,
            workflow_id=workflow_id or None,
        )
        self._fetch_runs_worker.workflows_fetched.connect(self._runs_panel.set_workflows)
        self._fetch_runs_worker.runs_fetched.connect(self._on_runs_fetched)
        self._fetch_runs_worker.error.connect(self._on_fetch_runs_error)
        self._fetch_runs_worker.start()

    def _on_runs_fetched(self, data: dict) -> None:
        self._runs_panel.set_loading(False)
        self._runs_panel.populate_runs(data)
        total = data.get("total_count", 0)
        self._status_bar.showMessage(
            f"{self._current_repo}  ·  {total} runs", 5000
        )

    def _on_fetch_runs_error(self, msg: str) -> None:
        self._runs_panel.set_loading(False)
        self._status_bar.showMessage(f"Error loading runs: {msg}", 6000)

    # ----------------------------------------------------------------  Monitor
    def _toggle_monitor(self, repo: str) -> None:
        if repo in self._monitors:
            self._stop_monitor(repo)
        else:
            self._start_monitor_dialog(repo)

    def _start_monitor_dialog(self, repo: str) -> None:
        """Open the monitor config dialog and start the worker on acceptance."""
        monitored = self.config.get_monitored_repos()
        existing = monitored.get(repo, {})

        default_dir = str(Path(self.config.workspace) / repo)

        dlg = MonitorDialog(
            repo,
            current_download_dir=existing.get("download_dir", default_dir),
            current_interval=existing.get("poll_interval", 60),
            parent=self,
        )
        if dlg.exec():
            self.config.set_monitor(repo, dlg.download_dir, dlg.poll_interval)
            self._launch_monitor(repo, dlg.download_dir, dlg.poll_interval)

    def _launch_monitor(self, repo: str, download_dir: str, poll_interval: int) -> None:
        worker = MonitorWorker(
            repo=repo,
            token=self.config.token,
            download_dir=download_dir,
            poll_interval=poll_interval,
            config=self.config,
        )
        worker.status_update.connect(
            lambda msg, r=repo: self._on_monitor_status(r, msg)
        )
        worker.new_run_found.connect(
            lambda run, r=repo: self._on_new_run(r, run)
        )
        worker.download_started.connect(
            lambda run_id, r=repo: self._on_download_started(r, run_id)
        )
        worker.download_complete.connect(
            lambda run_id, files, r=repo: self._on_download_complete(r, run_id, files)
        )
        worker.download_failed.connect(
            lambda run_id, err, r=repo: self._on_download_failed(r, run_id, err)
        )
        worker.stopped.connect(lambda r=repo: self._on_monitor_stopped(r))
        worker.start()

        self._monitors[repo] = worker
        self._repo_panel.mark_monitored(repo, True)
        if self._current_repo == repo:
            self._runs_panel.set_monitored(True)
        self._update_status()
        self._runs_panel.append_log(f"🟢 Monitor started for {repo}")

    def _stop_monitor(self, repo: str) -> None:
        worker = self._monitors.get(repo)
        if worker:
            worker.stop()
        # UI update happens in _on_monitor_stopped signal

    def _on_monitor_stopped(self, repo: str) -> None:
        self._monitors.pop(repo, None)
        self._repo_panel.mark_monitored(repo, False)
        if self._current_repo == repo:
            self._runs_panel.set_monitored(False)
        self.config.remove_monitor(repo)
        self._update_status()
        self._runs_panel.append_log(f"⚫ Monitor stopped for {repo}")

    # Monitor signal handlers
    def _on_monitor_status(self, repo: str, msg: str) -> None:
        if self._current_repo == repo:
            self._runs_panel.append_log(msg)
        self._status_bar.showMessage(msg, 3000)

    def _on_new_run(self, repo: str, run: dict) -> None:
        run_num = run.get("run_number", "?")
        name = run.get("name", "")
        msg = f"🎉 New successful run #{run_num} ({name}) in {repo}"
        self._runs_panel.append_log(msg)

    def _on_download_started(self, repo: str, run_id: int) -> None:
        self._runs_panel.append_log(
            f"⬇  Downloading artifacts for run #{run_id} …"
        )

    def _on_download_complete(self, repo: str, run_id: int, files: list[str]) -> None:
        self._runs_panel.append_log(
            f"✅ Downloaded {len(files)} file(s) for run #{run_id}"
        )
        for path in files:
            self._runs_panel.append_log(f"   📄 {path}")

    def _on_download_failed(self, repo: str, run_id: int, err: str) -> None:
        self._runs_panel.append_log(
            f"❌ Download failed for run #{run_id}: {err}"
        )

    # ----------------------------------------------------------------  Restore
    def _restore_monitors(self) -> None:
        """On startup, re-launch all monitors that were active in the last session."""
        monitored = self.config.get_monitored_repos()
        for repo, cfg in monitored.items():
            default_dir = str(Path(self.config.workspace) / repo)
            download_dir = cfg.get("download_dir", default_dir)
            poll_interval = cfg.get("poll_interval", 60)
            self._launch_monitor(repo, download_dir, poll_interval)

    # ----------------------------------------------------------------  Status
    def _update_status(self) -> None:
        if not self.config.token:
            self._status_bar.showMessage("⚠ No token set — File → Settings")
            return
        n = len(self._monitors)
        if n:
            self._status_bar.showMessage(
                f"✅ Authenticated  ·  🟢 Monitoring {n} repo(s)"
            )
        else:
            self._status_bar.showMessage("✅ Authenticated")

    # ----------------------------------------------------------------  Close
    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Stop all monitor workers gracefully before closing."""
        for worker in list(self._monitors.values()):
            worker.stop()
        super().closeEvent(event)
