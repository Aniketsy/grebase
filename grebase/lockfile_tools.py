from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()

LOCKFILE_COMMANDS: dict[str, list[str]] = {
    "poetry.lock": ["poetry", "lock", "--no-update"],
    "Pipfile.lock": ["pipenv", "lock"],
    "package-lock.json": ["npm", "install"],
    "yarn.lock": ["yarn", "install"],
    "pnpm-lock.yaml": ["pnpm", "install"],
}


def get_lockfile_command(file_name: str) -> list[str] | None:
    return LOCKFILE_COMMANDS.get(file_name)


def is_tool_available(command: list[str]) -> bool:
    return shutil.which(command[0]) is not None


def strip_conflict_markers(repo_path: Path, file_name: str) -> None:
    full_path = repo_path / file_name
    if not full_path.exists():
        return
    content = full_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines(keepends=True)
    result: list[str] = []
    in_conflict = False
    for line in lines:
        if line.startswith("<<<<<<<"):
            in_conflict = True
            continue
        if line.startswith("======="):
            continue
        if line.startswith(">>>>>>>"):
            in_conflict = False
            continue
        if not in_conflict:
            result.append(line)
    full_path.write_text("".join(result), encoding="utf-8")


def has_yarn_merge_driver(repo_path: Path) -> bool:
    attributes_path = repo_path / ".gitattributes"
    if not attributes_path.exists():
        return False
    content = attributes_path.read_text(encoding="utf-8", errors="replace")
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "yarn.lock" in line and "merge=" in line and "yarn" in line:
            return True
    return False


def regenerate_lockfile(repo_path: Path, file_name: str) -> bool:
    command = get_lockfile_command(file_name)
    if not command:
        return False
    if not is_tool_available(command):
        return False
    console.print(
        f"[yellow]![/yellow] Regenerating {file_name} - package versions may change. "
        f"Review with: git diff -- {file_name}"
    )
    strip_conflict_markers(repo_path, file_name)
    result = subprocess.run(
        command,
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0
