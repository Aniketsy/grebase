from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import grebase.cli as cli


def _setup_audit_mocks(
    monkeypatch: pytest.MonkeyPatch, conflict_sequences: list[list[str]]
) -> Path:
    sequence = iter(conflict_sequences)

    repo_path = Path.cwd()
    git_dir = repo_path / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(cli, "ensure_git_repo", lambda *_: None)
    monkeypatch.setattr(cli, "get_current_branch", lambda *_: "feature")
    monkeypatch.setattr(cli, "detect_target_branch", lambda *_args, **_kwargs: "main")
    monkeypatch.setattr(cli, "select_remote", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "has_remote", lambda *_: False)
    monkeypatch.setattr(cli, "fetch", lambda *_: None)
    monkeypatch.setattr(cli, "rebase", lambda *_: SimpleNamespace(returncode=0, stderr=""))
    monkeypatch.setattr(cli, "diff_stat_range", lambda *_: "")
    monkeypatch.setattr(cli, "is_rebase_in_progress", lambda *_: False)
    monkeypatch.setattr(cli, "status_porcelain", lambda *_: "")
    monkeypatch.setattr(cli, "save_state", lambda *_: None)
    monkeypatch.setattr(cli, "get_conflict_files", lambda *_: next(sequence))
    monkeypatch.setattr(cli, "resolve_file", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(cli, "resolve_with_choice", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(cli, "add_files", lambda *_: None)
    monkeypatch.setattr(cli, "rebase_continue", lambda *_args, **_kwargs: None)

    return git_dir


def test_audit_log_records_choices(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    _setup_audit_mocks(monkeypatch, [["a.py"], []])

    monkeypatch.setattr(cli, "last_commit_for_file", lambda *_: "abc123 fix config")
    monkeypatch.setattr(cli, "prompt_conflict_action", lambda: "1")

    assert cli.run_workflow(interactive=True, audit=True) == 0

    log_path = tmp_path / ".git" / "grebase.log"
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "choice" in content
    assert "mine a.py" in content
