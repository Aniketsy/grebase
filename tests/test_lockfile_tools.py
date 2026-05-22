from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from grebase.lockfile_tools import get_lockfile_command, regenerate_lockfile


def test_get_lockfile_command_known() -> None:
    assert get_lockfile_command("poetry.lock") == ["poetry", "lock"]


def test_get_lockfile_command_unknown() -> None:
    assert get_lockfile_command("unknown.lock") is None


def test_regenerate_lockfile_runs_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
