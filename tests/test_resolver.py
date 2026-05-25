from pathlib import Path

import pytest

from grebase.config import GrebaseConfig
from grebase.conflict_resolver import resolve_file, resolve_with_both, resolve_with_choice
from grebase.rules import resolve_formatting, resolve_imports

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

    monkeypatch.setattr("grebase.conflict_resolver.is_tool_available", lambda *_: True)
    monkeypatch.setattr("grebase.conflict_resolver.regenerate_lockfile", lambda *_: True)
    assert resolve_file(tmp_path, "poetry.lock", config) is True


def test_resolve_lockfile_conflict_fails_when_regen_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file_path = tmp_path / "poetry.lock"
    file_path.write_text(_load("poetry.lock"), encoding="utf-8")
    config = GrebaseConfig(repo_path=tmp_path, target="origin/main")

    monkeypatch.setattr("grebase.conflict_resolver.is_tool_available", lambda *_: True)
    monkeypatch.setattr("grebase.conflict_resolver.regenerate_lockfile", lambda *_: False)
    assert resolve_file(tmp_path, "poetry.lock", config) is False


def test_resolve_with_choice_mine(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(_load("semantic_conflict.py"), encoding="utf-8")
    assert resolve_with_choice(tmp_path, "sample.py", "mine") is True
    assert "timeout = 120" in file_path.read_text(encoding="utf-8")


def test_resolve_with_choice_theirs(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(_load("semantic_conflict.py"), encoding="utf-8")
    assert resolve_with_choice(tmp_path, "sample.py", "theirs") is True
    assert "timeout = 30" in file_path.read_text(encoding="utf-8")


def test_resolve_formatting_rejects_indentation_change() -> None:
    assert resolve_formatting("    x = 1\n", "  x = 1\n") is None


def test_resolve_formatting_same_indentation_resolves() -> None:
    assert resolve_formatting("    x = 1\n", "    x=1\n") is not None


def test_resolve_imports_multiline_parens() -> None:
    current = "from os import (\n    path,\n    getcwd,\n)\n"
    incoming = "from os import environ\n"
    result = resolve_imports(current, incoming)
    assert result is not None
    assert "path" in result
    assert "getcwd" in result
    assert "environ" in result
    assert result.count("from os import") == 1


def test_resolve_imports_multiline_parens_three_names() -> None:
    current = "from typing import (\n    List,\n    Dict,\n    Optional,\n)\n"
    incoming = "from typing import Tuple\n"
    result = resolve_imports(current, incoming)
    assert result is not None
    assert all(name in result for name in ["List", "Dict", "Optional", "Tuple"])
    assert result.count("from typing import") == 1


def test_resolve_imports_respects_intentional_removal() -> None:
    base = "import os\nimport deprecated_module\n"
    current = "import os\nimport deprecated_module\n"
    incoming = "import os\nimport logging\n"
    result = resolve_imports(current, incoming, base=base)
    assert result is not None
    assert "import deprecated_module" not in result
    assert "import logging" in result


def test_resolve_import_conflict_keeps_star_import(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        """<<<<<<< HEAD
from os import *
=======
from os import path
>>>>>>> main
""",
        encoding="utf-8",
    )
    config = GrebaseConfig(repo_path=tmp_path, target="origin/main")
    assert resolve_file(tmp_path, "sample.py", config) is True
    text = file_path.read_text(encoding="utf-8")
    assert text.strip() == "from os import *"


def test_resolve_import_conflict_places_future_import_first(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        """<<<<<<< HEAD
from __future__ import annotations
import os
=======
from __future__ import annotations
import sys
>>>>>>> main
""",
        encoding="utf-8",
    )
    config = GrebaseConfig(repo_path=tmp_path, target="origin/main")
    assert resolve_file(tmp_path, "sample.py", config) is True
    text = file_path.read_text(encoding="utf-8")
    assert text.startswith("from __future__ import annotations\n")


def test_resolve_with_both_mine_first(tmp_path: Path) -> None:
    file_path = tmp_path / "api.py"
    file_path.write_text(
        "class A:\n<<<<<<< HEAD\n    def theirs(self): pass\n=======\n"
        "    def mine(self): pass\n>>>>>>> main\n",
        encoding="utf-8",
    )
    ok, preview = resolve_with_both(tmp_path, "api.py", mine_first=True)
    assert ok
    result = file_path.read_text(encoding="utf-8")
    mine_pos = result.index("def mine")
    theirs_pos = result.index("def theirs")
    assert mine_pos < theirs_pos
    assert "<<<<<<<" not in result
    assert preview == result


def test_resolve_with_both_theirs_first(tmp_path: Path) -> None:
    file_path = tmp_path / "api.py"
    file_path.write_text(
        "class A:\n<<<<<<< HEAD\n    def theirs(self): pass\n=======\n"
        "    def mine(self): pass\n>>>>>>> main\n",
        encoding="utf-8",
    )
    ok, preview = resolve_with_both(tmp_path, "api.py", mine_first=False)
    assert ok
    result = file_path.read_text(encoding="utf-8")
    mine_pos = result.index("def mine")
    theirs_pos = result.index("def theirs")
    assert theirs_pos < mine_pos
    assert "<<<<<<<" not in result
    assert preview == result


def test_resolve_with_both_blank_line_separator(tmp_path: Path) -> None:
    file_path = tmp_path / "api.py"
    file_path.write_text(
        "<<<<<<< HEAD\n    def theirs(self): pass\n=======\n"
        "    def mine(self): pass\n>>>>>>> main\n",
        encoding="utf-8",
    )
    _, preview = resolve_with_both(tmp_path, "api.py", mine_first=True)
    assert "\n\n" in preview
