from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextSegment:
    text: str


@dataclass(frozen=True)
class ConflictSegment:
    current: str
    incoming: str
    marker: str


Segment = TextSegment | ConflictSegment


def has_conflicts(text: str) -> bool:
    return "<<<<<<<" in text and "=======" in text and ">>>>>>>" in text


def parse_conflict_segments(text: str) -> list[Segment]:
    lines = text.splitlines(keepends=True)
    segments: list[Segment] = []
    buffer: list[str] = []
    idx = 0

    def flush_buffer() -> None:
        if buffer:
            segments.append(TextSegment("".join(buffer)))
            buffer.clear()

    while idx < len(lines):
        line = lines[idx]
        if line.startswith("<<<<<<<"):
            flush_buffer()
            idx += 1
            head_lines: list[str] = []
            incoming_lines: list[str] = []
            while idx < len(lines) and not lines[idx].startswith("======="):
                head_lines.append(lines[idx])
                idx += 1
            idx += 1
            while idx < len(lines) and not lines[idx].startswith(">>>>>>>"):
                incoming_lines.append(lines[idx])
                idx += 1
            marker = lines[idx].strip() if idx < len(lines) else ""
            idx += 1
            # During rebase, HEAD is the target branch; policy mapping is handled elsewhere.
            segments.append(ConflictSegment("".join(incoming_lines), "".join(head_lines), marker))
        else:
            buffer.append(line)
            idx += 1

    flush_buffer()
    return segments
