from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from .conflict_parser import ConflictSegment, parse_conflict_segments

console = Console()
MAX_LINES = 15


@dataclass(frozen=True)
class PreviewBlock:
    title: str
    lines: list[str]
    truncated: bool


def _build_block(title: str, text: str) -> PreviewBlock:
    lines = text.splitlines()
    if len(lines) > MAX_LINES:
        return PreviewBlock(title, lines[:MAX_LINES], True)
    return PreviewBlock(title, lines, False)


def _render_block(block: PreviewBlock, color: str) -> None:
    console.print(f"[blue]◆[/blue] {block.title}")
    if not block.lines:
        console.print("  [dim](empty)[/dim]")
        return
    for line in block.lines:
        console.print(f"  [{color}]{line}[/{color}]")
    if block.truncated:
        console.print("  [dim]...truncated...[/dim]")


def show_conflict_preview(file_path: Path, file_text: str) -> None:
    segments = parse_conflict_segments(file_text)
    conflicts = [segment for segment in segments if isinstance(segment, ConflictSegment)]
    if not conflicts:
        console.print("[dim]  No conflict preview available.[/dim]")
        return

    console.print(f"[blue]i[/blue] Conflict preview for {file_path.name}:")
    for index, segment in enumerate(conflicts, start=1):
        console.print(f"[dim]  Conflict {index}[/dim]")
        current_block = _build_block("Yours [1]", segment.current)
        incoming_block = _build_block("Theirs [2]", segment.incoming)
        _render_block(current_block, color="green")
        _render_block(incoming_block, color="yellow")
