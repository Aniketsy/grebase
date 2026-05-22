from __future__ import annotations

from pathlib import Path

from .config import GrebaseConfig
from .conflict_classifier import ConflictType, classify_conflict
from .conflict_parser import TextSegment, parse_conflict_segments
from .lockfile_tools import regenerate_lockfile
from .rules import resolve_docs, resolve_duplicate, resolve_formatting, resolve_imports

SAFE_TYPES = {
    ConflictType.IMPORTS,
    ConflictType.FORMATTING,
    ConflictType.DOCUMENTATION,
    ConflictType.DUPLICATE,
}


def resolve_file(repo_path: Path, file_path: str, config: GrebaseConfig) -> bool:
    full_path = repo_path / file_path
    text = full_path.read_text(encoding="utf-8")
    segments = parse_conflict_segments(text)
    conflict_type = classify_conflict(file_path, segments)

    if conflict_type == ConflictType.LOCKFILE:
        if config.safe_only:
            return False
        if config.dry_run:
            return True
        return regenerate_lockfile(repo_path, Path(file_path).name)

    if config.safe_only and conflict_type not in SAFE_TYPES:
        return False

    resolved_parts: list[str] = []
    for segment in segments:
        if isinstance(segment, TextSegment):
            resolved_parts.append(segment.text)
            continue
        if conflict_type == ConflictType.IMPORTS:
            resolved = resolve_imports(segment.current, segment.incoming)
        elif conflict_type == ConflictType.FORMATTING:
            resolved = resolve_formatting(segment.current, segment.incoming)
        elif conflict_type == ConflictType.DOCUMENTATION:
            resolved = resolve_docs(segment.current, segment.incoming)
        elif conflict_type == ConflictType.DUPLICATE:
            resolved = resolve_duplicate(segment.current, segment.incoming)
        else:
            resolved = None

        if resolved is None:
            return False
        resolved_parts.append(resolved)

    if not config.dry_run:
        full_path.write_text("".join(resolved_parts), encoding="utf-8")
    return True


def resolve_with_choice(repo_path: Path, file_path: str, choice: str) -> bool:
    full_path = repo_path / file_path
    text = full_path.read_text(encoding="utf-8")
    segments = parse_conflict_segments(text)
    resolved_parts: list[str] = []
    for segment in segments:
        if isinstance(segment, TextSegment):
            resolved_parts.append(segment.text)
            continue
        if choice == "current":
            resolved_parts.append(segment.current)
        elif choice == "incoming":
            resolved_parts.append(segment.incoming)
        else:
            return False
    full_path.write_text("".join(resolved_parts), encoding="utf-8")
    return True
