"""Thin wrappers around the GitHub REST API (synchronous, run from QThreads)."""

from __future__ import annotations

from typing import Optional

import requests

API_BASE = "https://api.github.com"
_ACCEPT = "application/vnd.github+json"
_API_VER = "2022-11-28"
_TIMEOUT = 20  # seconds


def make_headers(token: str) -> dict[str, str]:
    return {
        "Accept": _ACCEPT,
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": _API_VER,
    }


def get_user(token: str) -> dict:
    """Return the authenticated user's profile."""
    r = requests.get(f"{API_BASE}/user", headers=make_headers(token), timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


def list_repos(token: str) -> list[dict]:
    """Return all repos owned by the authenticated user, sorted by last-updated."""
    repos: list[dict] = []
    page = 1
    while True:
        r = requests.get(
            f"{API_BASE}/user/repos",
            headers=make_headers(token),
            params={"type": "owner", "per_page": 100, "page": page, "sort": "updated"},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        batch: list[dict] = r.json()
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def list_workflows(repo: str, token: str) -> list[dict]:
    """Return all workflow definitions for *repo*."""
    r = requests.get(
        f"{API_BASE}/repos/{repo}/actions/workflows",
        headers=make_headers(token),
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json().get("workflows", [])


def list_runs(
    repo: str,
    token: str,
    per_page: int = 50,
    page: int = 1,
    workflow_id: Optional[int] = None,
) -> dict:
    """Return a page of workflow runs.  The dict contains ``total_count`` and
    ``workflow_runs``."""
    if workflow_id:
        url = f"{API_BASE}/repos/{repo}/actions/workflows/{workflow_id}/runs"
    else:
        url = f"{API_BASE}/repos/{repo}/actions/runs"
    r = requests.get(
        url,
        headers=make_headers(token),
        params={"per_page": per_page, "page": page},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def list_artifacts(repo: str, run_id: int, token: str) -> list[dict]:
    """Return all artifacts for a workflow run."""
    r = requests.get(
        f"{API_BASE}/repos/{repo}/actions/runs/{run_id}/artifacts",
        headers=make_headers(token),
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json().get("artifacts", [])


def delete_run(repo: str, run_id: int, token: str) -> None:
    """Delete a workflow run (returns 204 on success)."""
    r = requests.delete(
        f"{API_BASE}/repos/{repo}/actions/runs/{run_id}",
        headers=make_headers(token),
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
