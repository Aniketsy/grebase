from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from grebase.cli import run_workflow


def _run_git(repo: Path, args: list[str]) -> None:
    subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True)


def _init_repo(repo: Path) -> None:
    _run_git(repo, ["init", "-b", "main"])
    _run_git(repo, ["config", "user.email", "test@example.com"])
    _run_git(repo, ["config", "user.name", "Test User"])


def _has_rebase(repo: Path) -> bool:
    result = subprocess.run(
        ["git", "rebase", "--show-current-patch"],
        cwd=str(repo),
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def _setup_semantic_conflict(repo: Path) -> Path:
    file_path = repo / "settings.py"
    file_path.write_text("timeout = 30\n", encoding="utf-8")
    _run_git(repo, ["add", "settings.py"])
    _run_git(repo, ["commit", "-m", "base"])

    _run_git(repo, ["checkout", "-b", "feature"])
    file_path.write_text("timeout = 60\n", encoding="utf-8")
    _run_git(repo, ["add", "settings.py"])
    _run_git(repo, ["commit", "-m", "feature change"])

    _run_git(repo, ["checkout", "main"])
    file_path.write_text("timeout = 120\n", encoding="utf-8")
    _run_git(repo, ["add", "settings.py"])
    _run_git(repo, ["commit", "-m", "main change"])

    _run_git(repo, ["checkout", "feature"])
    return file_path


def test_rebase_autoresolves_import_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if shutil.which("git") is None:
        pytest.skip("git not available")

    _init_repo(tmp_path)
    file_path = tmp_path / "app.py"

    file_path.write_text("import os\n", encoding="utf-8")
    _run_git(tmp_path, ["add", "app.py"])
    _run_git(tmp_path, ["commit", "-m", "base"])

    _run_git(tmp_path, ["checkout", "-b", "feature"])
    file_path.write_text("import sys\n", encoding="utf-8")
    _run_git(tmp_path, ["add", "app.py"])
    _run_git(tmp_path, ["commit", "-m", "feature change"])

    _run_git(tmp_path, ["checkout", "main"])
    file_path.write_text("import json\n", encoding="utf-8")
    _run_git(tmp_path, ["add", "app.py"])
    _run_git(tmp_path, ["commit", "-m", "main change"])

    _run_git(tmp_path, ["checkout", "feature"])

    monkeypatch.chdir(tmp_path)
    assert run_workflow(target="main", interactive=False) == 0

    merged = file_path.read_text(encoding="utf-8")
    assert "import sys" in merged
    assert "import json" in merged


def test_rebase_abort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if shutil.which("git") is None:
        pytest.skip("git not available")

    _init_repo(tmp_path)
    _setup_semantic_conflict(tmp_path)

    monkeypatch.chdir(tmp_path)
    assert run_workflow(target="main", interactive=False) == 2
    assert _has_rebase(tmp_path) is True

    assert run_workflow(abort_flag=True) == 0
    assert _has_rebase(tmp_path) is False


def test_rebase_skip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if shutil.which("git") is None:
        pytest.skip("git not available")

    _init_repo(tmp_path)
    _setup_semantic_conflict(tmp_path)

    monkeypatch.chdir(tmp_path)
    assert run_workflow(target="main", interactive=False) == 2
    assert _has_rebase(tmp_path) is True

    assert run_workflow(skip_flag=True) == 0
    assert _has_rebase(tmp_path) is False


def test_rebase_continue_after_manual_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if shutil.which("git") is None:
        pytest.skip("git not available")

    _init_repo(tmp_path)
    file_path = _setup_semantic_conflict(tmp_path)

    monkeypatch.chdir(tmp_path)
    assert run_workflow(target="main", interactive=False) == 2
    assert _has_rebase(tmp_path) is True

    file_path.write_text("timeout = 120\n", encoding="utf-8")
    _run_git(tmp_path, ["add", "settings.py"])

    assert run_workflow(continue_flag=True) == 0
    assert _has_rebase(tmp_path) is False


def test_rebase_fails_with_dirty_worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if shutil.which("git") is None:
        pytest.skip("git not available")

    _init_repo(tmp_path)
    (tmp_path / "dirty.txt").write_text("dirty", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    assert run_workflow(target="main") == 1


def test_rebase_fails_when_rebase_in_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if shutil.which("git") is None:
        pytest.skip("git not available")

    _init_repo(tmp_path)
    _setup_semantic_conflict(tmp_path)

    monkeypatch.chdir(tmp_path)
    assert run_workflow(target="main", interactive=False) == 2
    assert _has_rebase(tmp_path) is True

    assert run_workflow(target="main", interactive=False) == 2
