"""QThread-based background workers for all network / disk operations."""

from __future__ import annotations

import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

import requests
from PySide6.QtCore import QThread, Signal

from . import api
from .config import Config


# ---------------------------------------------------------------------------
# FetchReposWorker
# ---------------------------------------------------------------------------
class FetchReposWorker(QThread):
    repos_fetched = Signal(list)   # list[dict]
    error = Signal(str)

    def __init__(self, token: str) -> None:
        super().__init__()
        self.token = token

    def run(self) -> None:
        try:
            repos = api.list_repos(self.token)
            self.repos_fetched.emit(repos)
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# FetchUserWorker
# ---------------------------------------------------------------------------
class FetchUserWorker(QThread):
    user_fetched = Signal(dict)
    error = Signal(str)

    def __init__(self, token: str) -> None:
        super().__init__()
        self.token = token

    def run(self) -> None:
        try:
            user = api.get_user(self.token)
            self.user_fetched.emit(user)
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# FetchRunsWorker
# ---------------------------------------------------------------------------
class FetchRunsWorker(QThread):
    workflows_fetched = Signal(list)  # list[dict]
    runs_fetched = Signal(dict)       # raw API response dict
    error = Signal(str)

    def __init__(self, repo: str, token: str, page: int = 1,
                 workflow_id: int | None = None) -> None:
        super().__init__()
        self.repo = repo
        self.token = token
        self.page = page
        self.workflow_id = workflow_id

    def run(self) -> None:
        try:
            workflows = api.list_workflows(self.repo, self.token)
            self.workflows_fetched.emit(workflows)
            data = api.list_runs(
                self.repo, self.token,
                per_page=50, page=self.page,
                workflow_id=self.workflow_id,
            )
            self.runs_fetched.emit(data)
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# DeleteRunsWorker
# ---------------------------------------------------------------------------
class DeleteRunsWorker(QThread):
    progress = Signal(int, int)   # (current, total)
    run_deleted = Signal(int)     # run_id that was deleted
    done = Signal(int)            # total successfully deleted
    error = Signal(str)

    def __init__(self, repo: str, run_ids: list[int], token: str) -> None:
        super().__init__()
        self.repo = repo
        self.run_ids = list(run_ids)
        self.token = token

    def run(self) -> None:
        deleted = 0
        total = len(self.run_ids)
        for i, run_id in enumerate(self.run_ids, start=1):
            try:
                api.delete_run(self.repo, run_id, self.token)
                deleted += 1
                self.run_deleted.emit(run_id)
            except Exception as exc:
                self.error.emit(f"Run {run_id}: {exc}")
            self.progress.emit(i, total)
        self.done.emit(deleted)


# ---------------------------------------------------------------------------
# MonitorWorker
# ---------------------------------------------------------------------------
class MonitorWorker(QThread):
    status_update = Signal(str)           # human-readable status line
    new_run_found = Signal(dict)          # full run dict of new successful run
    download_started = Signal(int)        # run_id
    download_complete = Signal(int, list) # run_id, list[str] of local paths
    download_failed = Signal(int, str)    # run_id, error message
    stopped = Signal()

    def __init__(
        self,
        repo: str,
        token: str,
        download_dir: str,
        poll_interval: int,
        config: Config,
    ) -> None:
        super().__init__()
        self.repo = repo
        self.token = token
        self.download_dir = Path(download_dir)
        self.poll_interval = poll_interval
        self.config = config
        self._stop_flag = False
        self._known_ids: set[int] = config.get_downloaded_run_ids(repo)

    def stop(self) -> None:
        self._stop_flag = True

    def run(self) -> None:
        self.status_update.emit(f"[{self.repo}] Monitor started")
        while not self._stop_flag:
            try:
                self._poll()
            except Exception as exc:
                self.status_update.emit(f"[{self.repo}] Poll error: {exc}")
            # Sleep in 1-second slices so we can honour stop_flag quickly
            for _ in range(self.poll_interval):
                if self._stop_flag:
                    break
                time.sleep(1)
        self.status_update.emit(f"[{self.repo}] Monitor stopped")
        self.stopped.emit()

    def _poll(self) -> None:
        data = api.list_runs(self.repo, self.token, per_page=30)
        runs: list[dict] = data.get("workflow_runs", [])
        now = datetime.now().strftime("%H:%M:%S")
        self.status_update.emit(
            f"[{self.repo}] Checked {len(runs)} runs at {now}"
        )
        for run in runs:
            run_id: int = run["id"]
            if run_id in self._known_ids:
                continue
            if run.get("status") == "completed" and run.get("conclusion") == "success":
                self._known_ids.add(run_id)
                self.config.add_downloaded_run(self.repo, run_id)
                self.new_run_found.emit(run)
                self.download_started.emit(run_id)
                self._do_download(run_id)

    def _do_download(self, run_id: int) -> None:
        try:
            artifacts = api.list_artifacts(self.repo, run_id, self.token)
            if not artifacts:
                self.download_failed.emit(run_id, "No artifacts found")
                return
            headers = api.make_headers(self.token)
            all_files: list[str] = []
            for artifact in artifacts:
                if artifact.get("expired"):
                    continue
                url = artifact["archive_download_url"]
                files = _extract_zip(url, headers, self.download_dir)
                all_files.extend(str(f) for f in files)
            self.download_complete.emit(run_id, all_files)
        except Exception as exc:
            self.download_failed.emit(run_id, str(exc))


# ---------------------------------------------------------------------------
# Shared download helper (used by MonitorWorker)
# ---------------------------------------------------------------------------
def _extract_zip(url: str, headers: dict, output_dir: Path) -> list[Path]:
    """Download a zip from *url* and extract it flat into *output_dir*."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp_path = Path(tmp.name)
    try:
        r = requests.get(url, headers=headers, stream=True, timeout=120)
        r.raise_for_status()
        with tmp_path.open("wb") as fh:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
        extracted: list[Path] = []
        with ZipFile(tmp_path) as zf:
            temp_dir = Path(tempfile.mkdtemp())
            zf.extractall(temp_dir)
            for item in temp_dir.rglob("*"):
                if item.is_file() and item.name != "artifact.zip":
                    dest = output_dir / item.name
                    stem, suf = dest.stem, dest.suffix
                    counter = 1
                    while dest.exists():
                        dest = output_dir / f"{stem}_{counter}{suf}"
                        counter += 1
                    shutil.move(str(item), str(dest))
                    extracted.append(dest)
            shutil.rmtree(temp_dir, ignore_errors=True)
        return extracted
    finally:
        tmp_path.unlink(missing_ok=True)
