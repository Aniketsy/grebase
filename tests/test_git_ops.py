from types import SimpleNamespace
from pathlib import Path

import pytest

from grebase.exceptions import GitError
from grebase.git_ops import (
	has_remote,
	is_git_repo,
	is_rebase_in_progress,
	list_changed_files,
	list_conflict_files,
	run_git,
)


def test_run_git_raises_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(stdout="", stderr="boom", returncode=1)

    monkeypatch.setattr("grebase.git_ops.subprocess.run", fake_run)
    with pytest.raises(GitError):
        run_git(["status"], cwd=Path.cwd())


def test_run_git_allows_failure_when_check_false(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(stdout="ok", stderr="", returncode=1)

    monkeypatch.setattr("grebase.git_ops.subprocess.run", fake_run)
    result = run_git(["status"], cwd=Path.cwd(), check=False)
    assert result.returncode == 1


def test_is_git_repo_true(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_git(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(stdout=".git", stderr="", returncode=0)

    monkeypatch.setattr("grebase.git_ops.run_git", fake_run_git)
    assert is_git_repo(Path.cwd()) is True


def test_list_conflict_files(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_git(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(stdout="a.txt\nb.py\n", stderr="", returncode=0)

    monkeypatch.setattr("grebase.git_ops.run_git", fake_run_git)
    assert list_conflict_files(Path.cwd()) == ["a.txt", "b.py"]


def test_has_remote(monkeypatch: pytest.MonkeyPatch) -> None:
	def fake_run_git(*_args: object, **_kwargs: object) -> SimpleNamespace:
		return SimpleNamespace(stdout="origin\nupstream\n", stderr="", returncode=0)

	monkeypatch.setattr("grebase.git_ops.run_git", fake_run_git)
	assert has_remote(Path.cwd(), remote="origin") is True
	assert has_remote(Path.cwd(), remote="missing") is False


def test_is_rebase_in_progress(monkeypatch: pytest.MonkeyPatch) -> None:
	def fake_run_git(*_args: object, **_kwargs: object) -> SimpleNamespace:
		return SimpleNamespace(stdout="patch", stderr="", returncode=0)

	monkeypatch.setattr("grebase.git_ops.run_git", fake_run_git)
	assert is_rebase_in_progress(Path.cwd()) is True


def test_list_changed_files(monkeypatch: pytest.MonkeyPatch) -> None:
	def fake_run_git(*_args: object, **_kwargs: object) -> SimpleNamespace:
		return SimpleNamespace(stdout=" M file1.py\nA  file2.txt\n", stderr="", returncode=0)

	monkeypatch.setattr("grebase.git_ops.run_git", fake_run_git)
	assert list_changed_files(Path.cwd()) == ["file1.py", "file2.txt"]
