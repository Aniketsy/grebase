from __future__ import annotations

from collections import OrderedDict


def normalize_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def normalize_whitespace(text: str) -> str:
    return "".join(text.split())


def resolve_imports(current: str, incoming: str) -> str | None:
    lines = normalize_lines(current) + normalize_lines(incoming)
    # preserve order for simple import lines
    simple_seen: set[str] = set()
    simple_order: list[str] = []
    # group `from X import a, b` by module while preserving module order
    from_map: OrderedDict[str, set[str]] = OrderedDict()

    for line in lines:
        if line.startswith("from ") and " import " in line:
            parts = line.split(" import ", 1)
            module = parts[0][len("from ") :].strip()
            names_str = parts[1].strip()
            # remove surrounding parentheses if any
            if names_str.startswith("(") and names_str.endswith(")"):
                names_str = names_str[1:-1].strip()
            names = [n.strip() for n in names_str.split(",") if n.strip()]
            if module not in from_map:
                from_map[module] = set()
            from_map[module].update(names)
        else:
            if line not in simple_seen:
                simple_seen.add(line)
                simple_order.append(line)

    parts: list[str] = []
    parts.extend(simple_order)
    for module, names in from_map.items():
        if not names:
            continue
        # deterministic ordering
        ordered_names = sorted(names)
        parts.append(f"from {module} import {', '.join(ordered_names)}")

    if not parts:
        return None
    return "\n".join(parts) + "\n"


def resolve_formatting(current: str, incoming: str) -> str | None:
    if normalize_whitespace(current) == normalize_whitespace(incoming):
        return current
    return None


def resolve_duplicate(current: str, incoming: str) -> str | None:
    # if both sides are empty, don't silently write an empty block; prompt instead
    if not normalize_lines(current) and not normalize_lines(incoming):
        return None
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
