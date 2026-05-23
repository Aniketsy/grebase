from __future__ import annotations

from collections import OrderedDict


def normalize_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def normalize_whitespace(text: str) -> str:
    return "".join(text.split())


def resolve_imports(current: str, incoming: str) -> str | None:
    lines = normalize_lines(current) + normalize_lines(incoming)
    ordered: OrderedDict[str, None] = OrderedDict()
    for line in lines:
        ordered.setdefault(line, None)
    if not ordered:
        return None
    return "\n".join(ordered.keys()) + "\n"


def resolve_formatting(current: str, incoming: str) -> str | None:
    if normalize_whitespace(current) == normalize_whitespace(incoming):
        return current
    return None


def resolve_duplicate(current: str, incoming: str) -> str | None:
    if normalize_lines(current) == normalize_lines(incoming):
        return current
    return None


def resolve_docs(current: str, incoming: str) -> str | None:
    combined = []
    seen = set()
    for line in current.splitlines():
        if line not in seen:
            combined.append(line)
            seen.add(line)
    for line in incoming.splitlines():
        if line not in seen:
            combined.append(line)
            seen.add(line)
    if not combined:
        return None
    return "\n".join(combined) + "\n"
