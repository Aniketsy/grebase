from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .utils import resolve_repo_paths


@dataclass(frozen=True)
class AuditEvent:
    timestamp: str
    action: str
    detail: str


def _audit_path(repo_path: Path) -> Path:
    return resolve_repo_paths(repo_path).git_dir / "grebase.log"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_audit(repo_path: Path, action: str, detail: str) -> None:
    path = _audit_path(repo_path)
    event = AuditEvent(timestamp=_now_iso(), action=action, detail=detail)
    line = f"{event.timestamp} | {event.action} | {event.detail}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
