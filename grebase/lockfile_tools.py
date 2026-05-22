from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


LOCKFILE_COMMANDS: dict[str, list[str]] = {
    "poetry.lock": ["poetry", "lock"],
    "Pipfile.lock": ["pipenv", "lock"],
    "package-lock.json": ["npm", "ci"],
    "yarn.lock": ["yarn", "install"],
    "pnpm-lock.yaml": ["pnpm", "install"],
}


def get_lockfile_command(file_name: str) -> list[str] | None:
    return LOCKFILE_COMMANDS.get(file_name)


def is_tool_available(command: list[str]) -> bool:
    return shutil.which(command[0]) is not None


def regenerate_lockfile(repo_path: Path, file_name: str) -> bool:
    command = get_lockfile_command(file_name)
    if not command:
        return False
    if not is_tool_available(command):
        return False
    result = subprocess.run(
        command,
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0
