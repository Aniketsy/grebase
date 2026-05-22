from __future__ import annotations

from pathlib import Path

from .git_ops import get_default_remote_branch, has_remote


def detect_target_branch(repo_path: Path, target: str | None, remote: str = "origin") -> str:
    if target:
        return target
    if has_remote(repo_path, remote=remote):
        return f"{remote}/{get_default_remote_branch(repo_path, remote=remote)}"
    return "main"
