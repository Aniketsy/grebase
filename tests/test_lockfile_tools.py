from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from grebase.lockfile_tools import (
    get_lockfile_command,
    regenerate_lockfile,
    strip_conflict_markers,
)


def test_get_lockfile_command_known() -> None:
    assert get_lockfile_command("poetry.lock") == ["poetry", "lock", "--no-update"]


def test_get_lockfile_command_unknown() -> None:
    assert get_lockfile_command("unknown.lock") is None


def test_regenerate_lockfile_runs_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "poetry.lock").write_text("content\n", encoding="utf-8")

    def fake_which(_cmd: str) -> str:
        return "C:/bin/tool"

    def fake_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("grebase.lockfile_tools.shutil.which", fake_which)
    monkeypatch.setattr("grebase.lockfile_tools.subprocess.run", fake_run)
    assert regenerate_lockfile(tmp_path, "poetry.lock") is True


def test_regenerate_lockfile_missing_tool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("grebase.lockfile_tools.shutil.which", lambda _cmd: None)
    assert regenerate_lockfile(tmp_path, "poetry.lock") is False


def test_strip_conflict_markers_removes_markers(tmp_path: Path) -> None:
    content = (
        "before\n"
        "<<<<<<< HEAD\n"
        "ours line\n"
        "=======\n"
        "theirs line\n"
        ">>>>>>> main\n"
        "after\n"
    )
    path = tmp_path / "yarn.lock"
    path.write_text(content, encoding="utf-8")

    strip_conflict_markers(tmp_path, "yarn.lock")
    result = path.read_text(encoding="utf-8")

    assert "<<<<<<<" not in result
    assert "=======" not in result
    assert ">>>>>>>" not in result
    assert "before\n" in result
    assert "after\n" in result
    assert "ours line" not in result
    assert "theirs line" not in result


def test_npm_uses_install_not_ci() -> None:
    assert get_lockfile_command("package-lock.json") == ["npm", "install"]


def test_poetry_uses_no_update_flag() -> None:
    command = get_lockfile_command("poetry.lock")
    assert command is not None
    assert "--no-update" in command


def test_regenerate_strips_markers_before_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "yarn.lock").write_text(
        "<<<<<<< HEAD\nversion: 1\n=======\nversion: 2\n>>>>>>> main\n",
        encoding="utf-8",
    )

    seen_content: dict[str, str] = {}

    def fake_which(_cmd: str) -> str:
        return "C:/bin/tool"

    def fake_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        seen_content["content"] = (tmp_path / "yarn.lock").read_text(encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("grebase.lockfile_tools.shutil.which", fake_which)
    monkeypatch.setattr("grebase.lockfile_tools.subprocess.run", fake_run)

    assert regenerate_lockfile(tmp_path, "yarn.lock") is True
    assert "<<<<<<<" not in seen_content["content"]
