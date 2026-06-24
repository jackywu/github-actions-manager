"""Persistent application configuration stored at ~/.github-actions-manager/config.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import platformdirs

APP_NAME = "github-actions-manager"
CONFIG_DIR = platformdirs.user_config_path(APP_NAME)
CONFIG_FILE = CONFIG_DIR / "config.json"

CACHE_DIR = platformdirs.user_cache_path(APP_NAME)
CACHE_FILE = CACHE_DIR / "repos_cache.json"

_DEFAULTS: dict[str, Any] = {
    "github_token": "",
    "workspace": str(Path.home() / "github_helper"),
    "theme": "light",
    "monitored_repos": {},
    "starred_repos": [],
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

        if CACHE_FILE.exists():
            try:
                with CACHE_FILE.open("r", encoding="utf-8") as fh:
                    self._data["cached_repos"] = json.load(fh)
            except Exception:
                pass

    def save(self) -> None:
        """Persist config to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data_to_save = {k: v for k, v in self._data.items() if k != "cached_repos"}
        with CONFIG_FILE.open("w", encoding="utf-8") as fh:
            json.dump(data_to_save, fh, indent=2, ensure_ascii=False)

    def save_cache(self) -> None:
        """Persist cache to disk."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with CACHE_FILE.open("w", encoding="utf-8") as fh:
            json.dump(self._data.get("cached_repos", []), fh, indent=2, ensure_ascii=False)

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

    def get_starred_repos(self) -> set[str]:
        """Return a set of starred repos."""
        return set(self._data.get("starred_repos", []))

    def set_starred(self, repo: str, is_starred: bool) -> None:
        """Add or remove a repo from the starred list."""
        starred = set(self._data.get("starred_repos", []))
        if is_starred:
            starred.add(repo)
        else:
            starred.discard(repo)
        self._data["starred_repos"] = list(starred)
        self.save()

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

    # ------------------------------------------------------------- Cache ----
    @property
    def cached_repos(self) -> list[dict]:
        return self._data.get("cached_repos", [])

    @cached_repos.setter
    def cached_repos(self, value: list[dict]) -> None:
        self._data["cached_repos"] = value
        self.save_cache()
