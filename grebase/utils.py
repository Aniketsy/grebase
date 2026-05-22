from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepoPaths:
    root: Path
    git_dir: Path


def resolve_repo_paths(repo_path: Path) -> RepoPaths:
    git_dir = repo_path / ".git"
    return RepoPaths(root=repo_path, git_dir=git_dir)
