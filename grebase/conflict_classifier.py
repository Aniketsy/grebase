from __future__ import annotations

from enum import Enum
from pathlib import Path

from .conflict_parser import ConflictSegment, Segment


class ConflictType(str, Enum):
    IMPORTS = "imports"
    FORMATTING = "formatting"
    DOCUMENTATION = "documentation"
    LOCKFILE = "lockfile"
    DUPLICATE = "duplicate"
    SEMANTIC = "semantic"


LOCKFILES = {
    "package-lock.json",
    "poetry.lock",
    "Pipfile.lock",
    "yarn.lock",
    "pnpm-lock.yaml",
}

DOC_EXTENSIONS = {".md", ".rst", ".adoc", ".txt"}

# Explicit dependency files that should be treated as semantic (not docs)
DEPENDENCY_FILES = {
    "requirements.txt",
    "requirements-dev.txt",
    "constraints.txt",
}


def _is_import_block(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    for line in lines:
        parts = line.split()
        if not parts or parts[0] not in {"import", "from"}:
            return False
    return True


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _normalize_whitespace(text: str) -> str:
    return "".join(text.split())


def _is_formatting_only(current: str, incoming: str) -> bool:
    return _normalize_whitespace(current) == _normalize_whitespace(incoming)


def _is_duplicate(current: str, incoming: str) -> bool:
    return _normalize(current) == _normalize(incoming)


def classify_conflict(file_path: str, segments: list[Segment]) -> ConflictType:
    path = Path(file_path)
    if path.name in LOCKFILES:
        return ConflictType.LOCKFILE
    if path.name in DEPENDENCY_FILES:
        return ConflictType.SEMANTIC
    if path.suffix.lower() in DOC_EXTENSIONS:
        return ConflictType.DOCUMENTATION

    conflict_segments = [segment for segment in segments if isinstance(segment, ConflictSegment)]
    if not conflict_segments:
        return ConflictType.SEMANTIC

    if all(
        _is_import_block(seg.current) and _is_import_block(seg.incoming)
        for seg in conflict_segments
    ):
        return ConflictType.IMPORTS
    if all(_is_duplicate(seg.current, seg.incoming) for seg in conflict_segments):
        return ConflictType.DUPLICATE
    if all(_is_formatting_only(seg.current, seg.incoming) for seg in conflict_segments):
        return ConflictType.FORMATTING

    return ConflictType.SEMANTIC
