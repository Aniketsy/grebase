from __future__ import annotations

from pathlib import Path

from grebase.branch_detector import detect_target_branch, select_remote


def test_select_remote_prefers_upstream(monkeypatch) -> None:
    monkeypatch.setattr("grebase.branch_detector.has_remote", lambda *_args, **_kwargs: True)
    assert select_remote(Path.cwd(), preferred="auto") == "upstream"


def test_select_remote_uses_origin_when_no_upstream(monkeypatch) -> None:
    def _has_remote(_path: Path, remote: str = "origin") -> bool:
        return remote == "origin"

    monkeypatch.setattr("grebase.branch_detector.has_remote", _has_remote)
    assert select_remote(Path.cwd(), preferred="auto") == "origin"


def test_select_remote_none_when_missing(monkeypatch) -> None:
    monkeypatch.setattr("grebase.branch_detector.has_remote", lambda *_args, **_kwargs: False)
    assert select_remote(Path.cwd(), preferred="auto") is None


def test_detect_target_branch_with_remote(monkeypatch) -> None:
    monkeypatch.setattr("grebase.branch_detector.has_remote", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("grebase.branch_detector.get_default_remote_branch", lambda *_args, **_kwargs: "main")
    assert detect_target_branch(Path.cwd(), None, remote="origin") == "origin/main"


def test_detect_target_branch_without_remote(monkeypatch) -> None:
    monkeypatch.setattr("grebase.branch_detector.has_remote", lambda *_args, **_kwargs: False)
    assert detect_target_branch(Path.cwd(), None, remote=None) == "main"
