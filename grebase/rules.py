from __future__ import annotations

from collections import OrderedDict
from typing import TypedDict


class ImportGroup(TypedDict):
    star: bool
    names: set[str]


def normalize_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def normalize_whitespace(text: str) -> str:
    return "".join(text.split())


def _rejoin_multiline_imports(lines: list[str]) -> list[str]:
    # collapse parenthesized import blocks so they can be merged as a single statement
    result: list[str] = []
    buffer = ""
    in_paren = False
    for line in lines:
        if not in_paren:
            if line.startswith("from ") and line.endswith("("):
                buffer = line
                in_paren = True
            else:
                result.append(line)
        else:
            buffer += " " + line.strip()
            if line.strip() == ")":
                result.append(buffer)
                buffer = ""
                in_paren = False
    if buffer:
        result.append(buffer)
    return result


def resolve_imports(current: str, incoming: str) -> str | None:
    raw_lines = normalize_lines(current) + normalize_lines(incoming)
    lines = _rejoin_multiline_imports(raw_lines)
    # preserve order for plain imports and `from ... import ...` groups separately
    simple_seen: set[str] = set()
    simple_order: list[str] = []
    future_order: list[str] = []
    # group `from X import a, b` by module while preserving module order
    from_map: OrderedDict[str, ImportGroup] = OrderedDict()

    for line in lines:
        if line.startswith("from __future__ import "):
            if line not in simple_seen:
                simple_seen.add(line)
                future_order.append(line)
            continue
        if line.startswith("from ") and " import " in line:
            split_parts = line.split(" import ", 1)
            module = split_parts[0][len("from ") :].strip()
            names_str = split_parts[1].strip()
            # remove surrounding parentheses if any
            if names_str.startswith("(") and names_str.endswith(")"):
                names_str = names_str[1:-1].strip()
            names = {n.strip() for n in names_str.split(",") if n.strip()}
            if module not in from_map:
                from_map[module] = {"star": False, "names": set()}
            entry = from_map[module]
            if "*" in names:
                entry["star"] = True
                entry["names"] = set()
                continue
            if entry["star"]:
                continue
            entry["names"].update(names)
        else:
            if line not in simple_seen:
                simple_seen.add(line)
                simple_order.append(line)

    resolved_lines: list[str] = []
    # __future__ imports must stay at the top of the file
    resolved_lines.extend(future_order)
    resolved_lines.extend(simple_order)
    for module, entry in from_map.items():
        if entry["star"]:
            resolved_lines.append(f"from {module} import *")
            continue
        if not entry["names"]:
            continue
        ordered_names = sorted(entry["names"])
        resolved_lines.append(f"from {module} import {', '.join(ordered_names)}")

    if not resolved_lines:
        return None
    return "\n".join(resolved_lines) + "\n"


def resolve_formatting(current: str, incoming: str) -> str | None:
    current_lines = current.splitlines()
    incoming_lines = incoming.splitlines()
    if len(current_lines) == len(incoming_lines):
        for current_line, incoming_line in zip(current_lines, incoming_lines):
            current_indent = len(current_line) - len(current_line.lstrip())
            incoming_indent = len(incoming_line) - len(incoming_line.lstrip())
            if current_indent != incoming_indent:
                return None
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
