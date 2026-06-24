"""Persistent application configuration stored at ~/.github-actions-manager/config.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".github-actions-manager"
CONFIG_FILE = CONFIG_DIR / "config.json"

_DEFAULTS: dict[str, Any] = {
    "github_token": "",
    "workspace": str(Path.home() / "github_helper"),
    "theme": "light",
    "monitored_repos": {},
}


class Config:
    """Thread-safe (read / write) application configuration."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {k: v for k, v in _DEFAULTS.items()}
        self.load()

    # ------------------------------------------------------------------ I/O --
    def load(self) -> None:
        """Load config from disk (silently ignores errors)."""
        if CONFIG_FILE.exists():
            try:
                with CONFIG_FILE.open("r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                    self._data.update(loaded)
            except Exception:
                pass

    def save(self) -> None:
        """Persist config to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with CONFIG_FILE.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------- Token ----
    @property
    def token(self) -> str:
        return self._data.get("github_token", "")

    @token.setter
    def token(self, value: str) -> None:
        self._data["github_token"] = value
        self.save()

    # ------------------------------------------------------------- Workspace ----
    @property
    def workspace(self) -> str:
        return self._data.get("workspace", str(Path.home() / "github_helper"))

    @workspace.setter
    def workspace(self, value: str) -> None:
        self._data["workspace"] = value
        self.save()

    # ------------------------------------------------------------- Theme ----
    @property
    def theme(self) -> str:
        return self._data.get("theme", "light")

    @theme.setter
    def theme(self, value: str) -> None:
        self._data["theme"] = value
        self.save()

    # ------------------------------------------------------- Monitoring ----
    def get_monitored_repos(self) -> dict[str, dict]:
        """Return a copy of the monitored repos dict."""
        return dict(self._data.get("monitored_repos", {}))

    def set_monitor(self, repo: str, download_dir: str, poll_interval: int) -> None:
        """Add or update a monitoring entry for *repo*."""
        repos: dict = self._data.setdefault("monitored_repos", {})
        existing = repos.get(repo, {})
        repos[repo] = {
            "download_dir": download_dir,
            "poll_interval": poll_interval,
            # preserve already-downloaded run ids
            "downloaded_run_ids": existing.get("downloaded_run_ids", []),
        }
        self.save()

    def remove_monitor(self, repo: str) -> None:
        """Remove a monitoring entry for *repo*."""
        repos: dict = self._data.get("monitored_repos", {})
        repos.pop(repo, None)
        self.save()

    def add_downloaded_run(self, repo: str, run_id: int) -> None:
        """Record that *run_id* has already been downloaded for *repo*."""
        repos: dict = self._data.get("monitored_repos", {})
        if repo not in repos:
            return
        ids: list = repos[repo].setdefault("downloaded_run_ids", [])
        if run_id not in ids:
            ids.append(run_id)
        self.save()

    def get_downloaded_run_ids(self, repo: str) -> set[int]:
        """Return the set of run IDs already downloaded for *repo*."""
        repos = self._data.get("monitored_repos", {})
        cfg = repos.get(repo, {})
        return set(cfg.get("downloaded_run_ids", []))
