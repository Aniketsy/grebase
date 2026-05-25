from __future__ import annotations

import ast
from pathlib import Path

from rich.console import Console

from .config import GrebaseConfig
from .conflict_classifier import ConflictType, classify_conflict
from .conflict_parser import TextSegment, parse_conflict_segments
from .lockfile_tools import (
    get_lockfile_command,
    has_yarn_merge_driver,
    is_tool_available,
    regenerate_lockfile,
)
from .prompts import prompt_lockfile_regen
from .rules import resolve_docs, resolve_duplicate, resolve_formatting, resolve_imports

console = Console()

SAFE_TYPES = {
    ConflictType.IMPORTS,
    ConflictType.FORMATTING,
    ConflictType.DOCUMENTATION,
    ConflictType.DUPLICATE,
}


def _validate_syntax(file_path: Path) -> tuple[bool, str]:
    if file_path.suffix not in {".py", ".pyw"}:
        return True, ""
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        ast.parse(source)
        return True, ""
    except SyntaxError as exc:
        message = f"line {exc.lineno}: {exc.msg}" if exc.lineno else exc.msg
        return False, message


def resolve_file(
    repo_path: Path,
    file_path: str,
    config: GrebaseConfig,
    base_content: str | None = None,
) -> bool:
    full_path = repo_path / file_path
    original_text = full_path.read_text(encoding="utf-8")
    segments = parse_conflict_segments(original_text)
    conflict_type = classify_conflict(file_path, segments)

    if conflict_type == ConflictType.LOCKFILE:
        file_name = Path(file_path).name
        if config.safe_only:
            return False
        if config.dry_run:
            return True
        command = get_lockfile_command(file_name)
        if not command or not is_tool_available(command):
            return False
        if file_name == "yarn.lock" and has_yarn_merge_driver(repo_path):
            console.print(
                "[yellow]![/yellow] Detected yarn merge driver in .gitattributes. "
                "Skipping auto-regeneration for yarn.lock."
            )
            return False
        if config.interactive:
            console.print(
                f"[yellow]![/yellow] {file_name} is a lockfile. "
                "Regenerating may change package versions."
            )
            if not prompt_lockfile_regen(file_name, command):
                return False
        return regenerate_lockfile(repo_path, file_name)

    if config.safe_only and conflict_type not in SAFE_TYPES:
        return False

    resolved_parts: list[str] = []
    for segment in segments:
        if isinstance(segment, TextSegment):
            resolved_parts.append(segment.text)
            continue
        if conflict_type == ConflictType.IMPORTS:
            resolved = resolve_imports(segment.current, segment.incoming, base=base_content)
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
        valid, _error = _validate_syntax(full_path)
        if not valid:
            full_path.write_text(original_text, encoding="utf-8")
            return False
    return True


def resolve_with_choice(repo_path: Path, file_path: str, choice: str) -> bool:
    full_path = repo_path / file_path
    text = full_path.read_text(encoding="utf-8")
    segments = parse_conflict_segments(text)
    resolved_parts: list[str] = []
    normalized = choice.strip().lower()
    for segment in segments:
        if isinstance(segment, TextSegment):
            resolved_parts.append(segment.text)
            continue
        if normalized in {"mine", "current"}:
            resolved_parts.append(segment.current)
        elif normalized in {"theirs", "incoming"}:
            resolved_parts.append(segment.incoming)
        else:
            return False
    full_path.write_text("".join(resolved_parts), encoding="utf-8")
    return True


def resolve_with_both(
    repo_path: Path,
    file_path: str,
    mine_first: bool = True,
) -> tuple[bool, str]:
    """
    Concatenate both sides of every conflict in the file.
    mine_first=True: current then incoming
    mine_first=False: incoming then current
    """
    full_path = repo_path / file_path
    text = full_path.read_text(encoding="utf-8")
    segments = parse_conflict_segments(text)
    resolved_parts: list[str] = []

    for segment in segments:
        if isinstance(segment, TextSegment):
            resolved_parts.append(segment.text)
            continue
        mine = segment.current.rstrip("\n")
        theirs = segment.incoming.rstrip("\n")
        if mine_first:
            resolved_parts.append(mine + "\n\n" + theirs + "\n")
        else:
            resolved_parts.append(theirs + "\n\n" + mine + "\n")

    result = "".join(resolved_parts)
    full_path.write_text(result, encoding="utf-8")
    return True, result
