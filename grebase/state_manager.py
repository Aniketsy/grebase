from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime, timezone

from .utils import resolve_repo_paths


@dataclass
class GrebaseState:
    branch: str
    target: str
    started_at: str


def _state_path(repo_path: Path) -> Path:
    return resolve_repo_paths(repo_path).git_dir / "grebase_state.json"


def load_state(repo_path: Path) -> GrebaseState | None:
    path = _state_path(repo_path)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return GrebaseState(**data)


def save_state(repo_path: Path, branch: str, target: str) -> None:
    path = _state_path(repo_path)
    state = GrebaseState(
        branch=branch,
        target=target,
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    path.write_text(json.dumps(state.__dict__, indent=2), encoding="utf-8")
