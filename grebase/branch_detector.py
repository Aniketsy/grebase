from __future__ import annotations

from pathlib import Path

from .git_ops import get_default_remote_branch, has_remote


def select_remote(repo_path: Path, preferred: str = "auto") -> str | None:
    if preferred != "auto":
        return preferred
    if has_remote(repo_path, remote="upstream"):
        return "upstream"
    if has_remote(repo_path, remote="origin"):
        return "origin"
    return None


def detect_target_branch(repo_path: Path, target: str | None, remote: str | None = "origin") -> str:
    if target:
        return target
    if remote and has_remote(repo_path, remote=remote):
        return f"{remote}/{get_default_remote_branch(repo_path, remote=remote)}"
    return "main"
