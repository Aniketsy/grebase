from __future__ import annotations

from pathlib import Path

from .exceptions import GitError
from .git_ops import is_git_repo


def ensure_git_repo(repo_path: Path) -> None:
    if not is_git_repo(repo_path):
        raise GitError("not a git repository")
