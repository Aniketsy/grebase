from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GrebaseConfig:
    repo_path: Path
    target: str | None
    dry_run: bool = False
    interactive: bool = False
    safe_only: bool = False
    verbose: bool = False
