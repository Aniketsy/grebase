from __future__ import annotations

from pathlib import Path

from .git_ops import list_conflict_files


def get_conflict_files(repo_path: Path) -> list[str]:
    return list_conflict_files(repo_path)
