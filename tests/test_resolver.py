from pathlib import Path

import pytest

from grebase.config import GrebaseConfig
from grebase.conflict_resolver import resolve_file, resolve_with_choice

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_resolve_import_conflict(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(_load("import_conflict.py"), encoding="utf-8")
    config = GrebaseConfig(repo_path=tmp_path, target="origin/main")
    assert resolve_file(tmp_path, "sample.py", config) is True
    text = file_path.read_text(encoding="utf-8")
    assert "import os" in text
    assert "import sys" in text


def test_resolve_formatting_conflict(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(_load("formatting_conflict.txt"), encoding="utf-8")
    config = GrebaseConfig(repo_path=tmp_path, target="origin/main")
    assert resolve_file(tmp_path, "sample.py", config) is True
    text = file_path.read_text(encoding="utf-8")
    assert "bar(3, 4)" in text


def test_resolve_docs_conflict(tmp_path: Path) -> None:
    file_path = tmp_path / "README.md"
    file_path.write_text(_load("docs_conflict.md"), encoding="utf-8")
    config = GrebaseConfig(repo_path=tmp_path, target="origin/main")
    assert resolve_file(tmp_path, "README.md", config) is True
    text = file_path.read_text(encoding="utf-8")
    assert "item a" in text
    assert "item b" in text


def test_resolve_respects_safe_only(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(_load("semantic_conflict.py"), encoding="utf-8")
    config = GrebaseConfig(repo_path=tmp_path, target="origin/main", safe_only=True)
    assert resolve_file(tmp_path, "sample.py", config) is False


def test_resolve_dry_run_does_not_write(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    original = _load("import_conflict.py")
    file_path.write_text(original, encoding="utf-8")
    config = GrebaseConfig(repo_path=tmp_path, target="origin/main", dry_run=True)
    assert resolve_file(tmp_path, "sample.py", config) is True
    assert file_path.read_text(encoding="utf-8") == original


def test_resolve_lockfile_conflict_runs_regen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file_path = tmp_path / "poetry.lock"
    file_path.write_text(_load("poetry.lock"), encoding="utf-8")
    config = GrebaseConfig(repo_path=tmp_path, target="origin/main")

    monkeypatch.setattr("grebase.conflict_resolver.regenerate_lockfile", lambda *_: True)
    assert resolve_file(tmp_path, "poetry.lock", config) is True


def test_resolve_lockfile_conflict_fails_when_regen_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file_path = tmp_path / "poetry.lock"
    file_path.write_text(_load("poetry.lock"), encoding="utf-8")
    config = GrebaseConfig(repo_path=tmp_path, target="origin/main")

    monkeypatch.setattr("grebase.conflict_resolver.regenerate_lockfile", lambda *_: False)
    assert resolve_file(tmp_path, "poetry.lock", config) is False


def test_resolve_with_choice_current(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(_load("semantic_conflict.py"), encoding="utf-8")
    assert resolve_with_choice(tmp_path, "sample.py", "current") is True
    assert "timeout = 30" in file_path.read_text(encoding="utf-8")
