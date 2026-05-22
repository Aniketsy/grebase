from __future__ import annotations

from pathlib import Path

import pytest

import grebase.cli as cli


def _setup_workflow_mocks(
    monkeypatch: pytest.MonkeyPatch, conflict_sequences: list[list[str]]
) -> list[tuple[str, str]]:
    sequence = iter(conflict_sequences)

    monkeypatch.setattr(cli, "ensure_git_repo", lambda *_: None)
    monkeypatch.setattr(cli, "get_current_branch", lambda *_: "feature")
    monkeypatch.setattr(cli, "detect_target_branch", lambda *_: "main")
    monkeypatch.setattr(cli, "has_remote", lambda *_: False)
    monkeypatch.setattr(cli, "fetch", lambda *_: None)
    monkeypatch.setattr(cli, "rebase", lambda *_: None)
    monkeypatch.setattr(cli, "diff_stat_range", lambda *_: "")
    monkeypatch.setattr(cli, "is_rebase_in_progress", lambda *_: False)
    monkeypatch.setattr(cli, "status_porcelain", lambda *_: "")
    monkeypatch.setattr(cli, "save_state", lambda *_: None)
    monkeypatch.setattr(cli, "get_conflict_files", lambda *_: next(sequence))
    monkeypatch.setattr(cli, "resolve_file", lambda *_: False)
    monkeypatch.setattr(cli, "add_files", lambda *_: None)
    monkeypatch.setattr(cli, "rebase_continue", lambda *_args, **_kwargs: None)

    captured: list[tuple[str, str]] = []

    def _resolve_with_choice(_repo_path: Path, file_path: str, choice: str) -> bool:
        captured.append((file_path, choice))
        return True

    monkeypatch.setattr(cli, "resolve_with_choice", _resolve_with_choice)
    return captured


def test_policy_current_applies_to_all(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    captured = _setup_workflow_mocks(monkeypatch, [["a.py", "b.py"], []])

    assert cli.run_workflow(policy="current", interactive=False) == 0
    assert captured == [("a.py", "current"), ("b.py", "current")]


def test_policy_incoming_applies_to_all(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    captured = _setup_workflow_mocks(monkeypatch, [["a.py", "b.py"], []])

    assert cli.run_workflow(policy="incoming", interactive=False) == 0
    assert captured == [("a.py", "incoming"), ("b.py", "incoming")]


def test_batch_choice_current_applies_to_remaining(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    captured = _setup_workflow_mocks(monkeypatch, [["a.py", "b.py"], []])

    prompt_calls = {"count": 0}

    def _prompt() -> str:
        prompt_calls["count"] += 1
        return "3"

    monkeypatch.setattr(cli, "prompt_conflict_action", _prompt)

    assert cli.run_workflow(interactive=True) == 0
    assert captured == [("a.py", "current"), ("b.py", "current")]
    assert prompt_calls["count"] == 1


def test_batch_choice_incoming_applies_to_remaining(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    captured = _setup_workflow_mocks(monkeypatch, [["a.py", "b.py"], []])

    prompt_calls = {"count": 0}

    def _prompt() -> str:
        prompt_calls["count"] += 1
        return "4"

    monkeypatch.setattr(cli, "prompt_conflict_action", _prompt)

    assert cli.run_workflow(interactive=True) == 0
    assert captured == [("a.py", "incoming"), ("b.py", "incoming")]
    assert prompt_calls["count"] == 1
