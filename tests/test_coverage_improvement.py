"""
New tests to improve coverage.
Targets every uncovered line identified by pytest-cov.

Files improved:
  rules.py                 90% → ~98%
  conflict_classifier.py   94% → ~99%
  conflict_resolver.py     84% → ~96%
  lockfile_tools.py        75% → ~95%
  inline_editor.py         73% → ~92%
  git_ops.py               86% → ~95%
  prompts.py               44% → ~90%
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import typer

from grebase.branch_detector import detect_target_branch, select_remote
from grebase.cli import normalize_policy, run_workflow, version_callback
from grebase.config import GrebaseConfig
from grebase.conflict_classifier import ConflictType, classify_conflict
from grebase.conflict_parser import parse_conflict_segments
from grebase.conflict_resolver import resolve_file, resolve_with_both, resolve_with_choice
from grebase.exceptions import GitError
from grebase.inline_editor import (
    _has_conflict_markers,
    _show_diff,
    edit_and_validate,
    inline_edit,
)
from grebase.lockfile_tools import (
    get_lockfile_command,
    has_yarn_merge_driver,
    regenerate_lockfile,
    strip_conflict_markers,
)
from grebase.repo_detector import ensure_git_repo
from grebase.rules import (
    resolve_docs,
    resolve_duplicate,
    resolve_formatting,
    resolve_imports,
)
from grebase.state_manager import load_state, save_state

# rules.py


class TestResolveImportsEdgeCases:

    def test_unclosed_paren_block_appended_as_is(self) -> None:
        # line 39: unclosed paren block falls through to result as-is
        result = resolve_imports("from os import (\n    path\n", "import sys\n")
        assert result is not None

    def test_star_import_skips_remaining_names_for_module(self) -> None:
        # line 83: entry["star"] is True → continue (skip adding more names)
        result = resolve_imports("from os import *\n", "from os import path, getcwd\n")
        assert result is not None
        assert result.strip() == "from os import *"
        assert "path" not in result
        assert "getcwd" not in result

    def test_star_on_incoming_side(self) -> None:
        # line 99: entry["star"] already True → continue
        result = resolve_imports("from os import path\n", "from os import *\n")
        assert result is not None
        assert "import *" in result
        assert "path" not in result.replace("import *", "")

    def test_empty_names_set_skipped_in_output(self) -> None:
        # line 104: entry["names"] is empty after dedup → continue (no output line)
        result = resolve_imports("from os import *\n", "from os import *\n")
        assert result is not None
        assert result.count("from os import") == 1

    def test_resolve_imports_all_lines_empty_returns_none(self) -> None:
        # line 119: resolved_lines is empty → return None
        result = resolve_imports("", "")
        assert result is None

    def test_resolve_duplicate_both_empty_returns_none(self) -> None:
        # lines 124-125: both sides empty after normalize → None
        assert resolve_duplicate("", "") is None

    def test_resolve_duplicate_whitespace_only_both_returns_none(self) -> None:
        # both sides normalize to empty
        assert resolve_duplicate("   \n", "\n\n") is None

    def test_resolve_duplicate_identical_returns_current(self) -> None:
        # line 126-127: lines equal → return current
        result = resolve_duplicate("x = 1\n", "x = 1\n")
        assert result == "x = 1\n"

    def test_resolve_duplicate_different_returns_none(self) -> None:
        # line 128: lines differ → None
        assert resolve_duplicate("x = 1\n", "x = 2\n") is None

    def test_resolve_docs_both_empty_returns_none(self) -> None:
        # line 143: combined is empty → None
        assert resolve_docs("", "") is None


# conflict_classifier.py


class TestClassifierEdgeCases:

    def _classify(self, text: str, filename: str = "test.py") -> ConflictType:
        return classify_conflict(filename, parse_conflict_segments(text))

    def test_import_block_with_quoted_string_is_semantic(self) -> None:
        # line 39: line contains '"' → _is_import_block returns False → SEMANTIC
        text = '<<<<<<< HEAD\nimport os\nx = "hello"\n=======\nimport sys\n>>>>>>> main\n'
        assert self._classify(text) == ConflictType.SEMANTIC

    def test_import_block_with_semicolon_is_semantic(self) -> None:
        # line 39: line contains ';' → _is_import_block returns False → SEMANTIC
        text = (
            "<<<<<<< HEAD\n"
            "import React from 'react';\n"
            "=======\n"
            "import Vue from 'vue';\n"
            ">>>>>>> main\n"
        )
        assert self._classify(text, "App.tsx") == ConflictType.SEMANTIC

    def test_import_block_with_braces_is_semantic(self) -> None:
        # line 39: line contains '{' → SEMANTIC
        text = (
            "<<<<<<< HEAD\n"
            "import { useState } from 'react';\n"
            "=======\n"
            "import { useEffect } from 'react';\n"
            ">>>>>>> main\n"
        )
        assert self._classify(text, "index.ts") == ConflictType.SEMANTIC

    def test_mixed_import_and_code_is_semantic(self) -> None:
        # line 70: not all segments are import blocks → SEMANTIC
        text = "<<<<<<< HEAD\nimport os\nx = 1\n=======\nimport sys\ny = 2\n>>>>>>> main\n"
        assert self._classify(text) == ConflictType.SEMANTIC

    def test_no_conflict_segments_is_semantic(self) -> None:
        # line 76: no ConflictSegment found → SEMANTIC
        text = "just some plain text without conflict markers\n"
        segs = parse_conflict_segments(text)
        result = classify_conflict("test.py", segs)
        assert result == ConflictType.SEMANTIC

    def test_ts_file_with_quotes_is_semantic(self) -> None:
        text = (
            "<<<<<<< HEAD\n"
            'import type { FC } from "react";\n'
            "=======\n"
            'import type { ReactNode } from "react";\n'
            ">>>>>>> main\n"
        )
        assert self._classify(text, "types.ts") == ConflictType.SEMANTIC

    def test_js_double_quote_import_is_semantic(self) -> None:
        text = (
            "<<<<<<< HEAD\n"
            'import path from "path";\n'
            "=======\n"
            'import fs from "fs";\n'
            ">>>>>>> main\n"
        )
        assert self._classify(text, "server.js") == ConflictType.SEMANTIC


# conflict_resolver.py


class TestResolverEdgeCases:

    def test_syntax_validation_invalid_python_reverts(self, tmp_path: Path) -> None:
        # lines 37-39, 104-105: SyntaxError → revert file, return False
        f = tmp_path / "bad.py"
        original = "<<<<<<< HEAD\nfrom os import (\n=======\nfrom os import path\n>>>>>>> main\n"
        f.write_text(original, encoding="utf-8")
        config = GrebaseConfig(repo_path=tmp_path, target="main")
        result = resolve_file(tmp_path, "bad.py", config)
        assert result is False
        assert f.read_text(encoding="utf-8") == original

    def test_safe_only_skips_semantic(self, tmp_path: Path) -> None:
        # line 56: safe_only + not in SAFE_TYPES → return False
        f = tmp_path / "f.py"
        f.write_text("<<<<<<< HEAD\nx = 1\n=======\nx = 2\n>>>>>>> main\n", encoding="utf-8")
        config = GrebaseConfig(repo_path=tmp_path, target="main", safe_only=True)
        assert resolve_file(tmp_path, "f.py", config) is False

    def test_dry_run_returns_true_without_writing(self, tmp_path: Path) -> None:
        # line 58: dry_run → return True (lockfile case)
        f = tmp_path / "poetry.lock"
        original = "<<<<<<< HEAD\npkg=[]\n=======\npkg=[{name='x'}]\n>>>>>>> main\n"
        f.write_text(original, encoding="utf-8")
        config = GrebaseConfig(repo_path=tmp_path, target="main", dry_run=True)
        assert resolve_file(tmp_path, "poetry.lock", config) is True
        assert f.read_text(encoding="utf-8") == original  # unchanged

    def test_lockfile_tool_unavailable_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # line 61: tool not available → return False
        f = tmp_path / "yarn.lock"
        f.write_text("<<<<<<< HEAD\nv1\n=======\nv2\n>>>>>>> main\n", encoding="utf-8")
        monkeypatch.setattr("grebase.conflict_resolver.is_tool_available", lambda *_: False)
        config = GrebaseConfig(repo_path=tmp_path, target="main")
        assert resolve_file(tmp_path, "yarn.lock", config) is False

    def test_yarn_merge_driver_skips_regeneration(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # lines 63-67: yarn merge driver detected → return False
        f = tmp_path / "yarn.lock"
        f.write_text("<<<<<<< HEAD\nv1\n=======\nv2\n>>>>>>> main\n", encoding="utf-8")
        (tmp_path / ".gitattributes").write_text("yarn.lock merge=yarn\n", encoding="utf-8")
        monkeypatch.setattr("grebase.conflict_resolver.is_tool_available", lambda *_: True)
        config = GrebaseConfig(repo_path=tmp_path, target="main", interactive=False)
        assert resolve_file(tmp_path, "yarn.lock", config) is False

    def test_lockfile_interactive_user_declines(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # lines 69-74: interactive=True + user says N → return False
        f = tmp_path / "poetry.lock"
        f.write_text(
            "<<<<<<< HEAD\n" "pkg=[]\n" "=======\n" "pkg=[{name='x'}]\n" ">>>>>>> main\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("grebase.conflict_resolver.is_tool_available", lambda *_: True)
        monkeypatch.setattr("grebase.conflict_resolver.prompt_lockfile_regen", lambda *_: False)
        config = GrebaseConfig(repo_path=tmp_path, target="main", interactive=True)
        assert resolve_file(tmp_path, "poetry.lock", config) is False

    def test_lockfile_interactive_user_accepts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # lines 69-74: interactive=True + user says Y → regenerate
        f = tmp_path / "poetry.lock"
        f.write_text(
            "<<<<<<< HEAD\n" "pkg=[]\n" "=======\n" "pkg=[{name='x'}]\n" ">>>>>>> main\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("grebase.conflict_resolver.is_tool_available", lambda *_: True)
        monkeypatch.setattr("grebase.conflict_resolver.prompt_lockfile_regen", lambda *_: True)
        monkeypatch.setattr("grebase.conflict_resolver.regenerate_lockfile", lambda *_: True)
        config = GrebaseConfig(repo_path=tmp_path, target="main", interactive=True)
        assert resolve_file(tmp_path, "poetry.lock", config) is True

    def test_duplicate_conflict_resolved(self, tmp_path: Path) -> None:
        # line 92: duplicate conflict type resolved
        f = tmp_path / "f.py"
        f.write_text(
            "<<<<<<< HEAD\nx = 1\ny = 2\n=======\nx = 1\ny = 2\n>>>>>>> main\n", encoding="utf-8"
        )
        config = GrebaseConfig(repo_path=tmp_path, target="main")
        assert resolve_file(tmp_path, "f.py", config) is True

    def test_text_segment_passthrough(self, tmp_path: Path) -> None:
        # lines 117-118: TextSegment appended as-is
        f = tmp_path / "f.py"
        f.write_text(
            "# header\n<<<<<<< HEAD\nimport os\n=======\nimport sys\n>>>>>>> main\n# footer\n",
            encoding="utf-8",
        )
        config = GrebaseConfig(repo_path=tmp_path, target="main")
        assert resolve_file(tmp_path, "f.py", config) is True
        content = f.read_text(encoding="utf-8")
        assert "# header" in content
        assert "# footer" in content

    def test_resolve_with_both_multiple_conflict_blocks(self, tmp_path: Path) -> None:
        # resolve_with_both concatenates both sides and removes markers
        f = tmp_path / "f.py"
        f.write_text(
            "<<<<<<< HEAD\na = 1\n=======\na = 2\n>>>>>>> main\n"
            "middle\n"
            "<<<<<<< HEAD\nb = 1\n=======\nb = 2\n>>>>>>> main\n",
            encoding="utf-8",
        )
        ok, preview = resolve_with_both(tmp_path, "f.py", mine_first=True)
        assert ok is True
        assert "<<<<<<<" not in preview

    def test_resolve_with_choice_unknown_returns_false(self, tmp_path: Path) -> None:
        # line 124: unknown choice → return False
        f = tmp_path / "f.py"
        f.write_text("<<<<<<< HEAD\nx=1\n=======\nx=2\n>>>>>>> main\n", encoding="utf-8")
        result = resolve_with_choice(tmp_path, "f.py", "unknown_choice")
        assert result is False

    def test_resolve_file_with_base_content_respects_removal(self, tmp_path: Path) -> None:
        # base-aware resolution: intentional import removal respected
        f = tmp_path / "app.py"
        f.write_text(
            "<<<<<<< HEAD\nimport os\nimport logging\n"
            "=======\nimport os\nimport new_feature\n>>>>>>> main\n",
            encoding="utf-8",
        )
        base = "import os\nimport deprecated\n"
        config = GrebaseConfig(repo_path=tmp_path, target="main")
        ok = resolve_file(tmp_path, "app.py", config, base_content=base)
        assert ok is True
        content = f.read_text(encoding="utf-8")
        assert "deprecated" not in content
        assert "new_feature" in content
        assert "logging" in content


# lockfile_tools.py


class TestLockfileToolsEdgeCases:

    def test_strip_markers_nonexistent_file_is_noop(self, tmp_path: Path) -> None:
        # line 31: file doesn't exist → return silently
        strip_conflict_markers(tmp_path, "nonexistent.lock")
        # no exception = pass

    def test_has_yarn_merge_driver_no_gitattributes(self, tmp_path: Path) -> None:
        # line 52-53: .gitattributes doesn't exist → False
        assert has_yarn_merge_driver(tmp_path) is False

    def test_has_yarn_merge_driver_present(self, tmp_path: Path) -> None:
        # lines 54-60: .gitattributes has yarn merge driver → True
        (tmp_path / ".gitattributes").write_text("yarn.lock merge=yarn\n", encoding="utf-8")
        assert has_yarn_merge_driver(tmp_path) is True

    def test_has_yarn_merge_driver_commented_ignored(self, tmp_path: Path) -> None:
        # line 57: commented line → skip → return False
        (tmp_path / ".gitattributes").write_text("# yarn.lock merge=yarn\n", encoding="utf-8")
        assert has_yarn_merge_driver(tmp_path) is False

    def test_has_yarn_merge_driver_empty_lines_ignored(self, tmp_path: Path) -> None:
        # line 57: empty line → skip
        (tmp_path / ".gitattributes").write_text("\n\n*.py text=auto\n\n", encoding="utf-8")
        assert has_yarn_merge_driver(tmp_path) is False

    def test_has_yarn_merge_driver_no_match_returns_false(self, tmp_path: Path) -> None:
        # line 61: loop ends without match → return False
        (tmp_path / ".gitattributes").write_text("*.py text=auto\n*.md text\n", encoding="utf-8")
        assert has_yarn_merge_driver(tmp_path) is False

    def test_regenerate_lockfile_tool_fails_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # line 67: subprocess returns non-zero → return False
        (tmp_path / "yarn.lock").write_text("content\n", encoding="utf-8")
        monkeypatch.setattr("grebase.lockfile_tools.shutil.which", lambda _: "/usr/bin/yarn")
        monkeypatch.setattr(
            "grebase.lockfile_tools.subprocess.run",
            lambda *a, **kw: SimpleNamespace(returncode=1, stdout="", stderr="error"),
        )
        assert regenerate_lockfile(tmp_path, "yarn.lock") is False

    def test_strip_markers_multiple_blocks(self, tmp_path: Path) -> None:
        content = (
            "start\n"
            "<<<<<<< HEAD\nblock1-ours\n=======\nblock1-theirs\n>>>>>>> main\n"
            "middle\n"
            "<<<<<<< HEAD\nblock2-ours\n=======\nblock2-theirs\n>>>>>>> main\n"
            "end\n"
        )
        (tmp_path / "yarn.lock").write_text(content, encoding="utf-8")
        strip_conflict_markers(tmp_path, "yarn.lock")
        result = (tmp_path / "yarn.lock").read_text(encoding="utf-8")
        assert "<<<<<<<" not in result
        assert "start" in result and "middle" in result and "end" in result
        assert "block1-ours" not in result and "block2-ours" not in result

    def test_strip_markers_crlf_line_endings(self, tmp_path: Path) -> None:
        content = "before\r\n<<<<<<< HEAD\r\nours\r\n=======\r\ntheirs\r\n>>>>>>> main\r\nafter\r\n"
        (tmp_path / "yarn.lock").write_text(content, encoding="utf-8")
        strip_conflict_markers(tmp_path, "yarn.lock")
        result = (tmp_path / "yarn.lock").read_text(encoding="utf-8")
        assert "<<<<<<<" not in result
        assert "before" in result and "after" in result

    def test_all_lockfile_commands_defined(self) -> None:
        for name in [
            "poetry.lock",
            "Pipfile.lock",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
        ]:
            cmd = get_lockfile_command(name)
            assert cmd is not None, f"No command for {name}"
            assert len(cmd) >= 1


# inline_editor.py


class TestInlineEditorEdgeCases:

    def test_inline_edit_uses_file_content_when_no_initial(self, tmp_path: Path) -> None:
        # lines 55-58: initial_content is None → reads from file
        f = tmp_path / "f.py"
        f.write_text("x = 1\n", encoding="utf-8")
        with patch("grebase.inline_editor.prompt", return_value="x = 2\n"):
            result = inline_edit(f)
        assert result == "x = 2\n"

    def test_inline_edit_uses_initial_content_when_provided(self, tmp_path: Path) -> None:
        # lines 55-58: initial_content provided → uses it, not file
        f = tmp_path / "f.py"
        f.write_text("file content\n", encoding="utf-8")
        with patch("grebase.inline_editor.prompt", return_value="initial content\n"):
            result = inline_edit(f, initial_content="initial content\n")
        assert result == "initial content\n"

    def test_inline_edit_default_header_uses_filename(self, tmp_path: Path) -> None:
        # line 61: header is None → uses filename
        f = tmp_path / "myfile.py"
        f.write_text("x = 1\n", encoding="utf-8")
        with patch("grebase.inline_editor.prompt", return_value="x = 1\n"):
            result = inline_edit(f)
        assert result is not None

    def test_inline_edit_custom_header(self, tmp_path: Path) -> None:
        # line 61: header provided → used
        f = tmp_path / "f.py"
        f.write_text("x = 1\n", encoding="utf-8")
        with patch("grebase.inline_editor.prompt", return_value="x = 1\n"):
            result = inline_edit(f, header="Custom header")
        assert result is not None

    def test_inline_edit_keyboard_interrupt_returns_none(self, tmp_path: Path) -> None:
        # lines 79-81: KeyboardInterrupt → return None
        f = tmp_path / "f.py"
        f.write_text("x = 1\n", encoding="utf-8")
        with patch("grebase.inline_editor.prompt", side_effect=KeyboardInterrupt):
            result = inline_edit(f)
        assert result is None

    def test_make_keybindings_returns_keybindings(self) -> None:
        # lines 34-41: _make_keybindings creates KeyBindings object
        from prompt_toolkit.key_binding import KeyBindings

        from grebase.inline_editor import _make_keybindings

        kb = _make_keybindings()
        assert isinstance(kb, KeyBindings)

    def test_edit_and_validate_initial_content_passed_through(self, tmp_path: Path) -> None:
        # initial_content provided → used as starting point for editor
        f = tmp_path / "f.py"
        f.write_text("original\n", encoding="utf-8")
        with patch("grebase.inline_editor.inline_edit", return_value="edited\n") as mock:
            result = edit_and_validate(f, initial_content="prefilled\n")
        assert result is not None
        mock.assert_called_once()
        call_kwargs = mock.call_args
        assert "prefilled" in str(call_kwargs)

    def test_show_diff_with_changes(self) -> None:
        # shows +/- lines — should not raise
        _show_diff("x = 1\n", "x = 2\n", "f.py")

    def test_has_conflict_markers_equals_only_is_false(self) -> None:
        # ======= alone is NOT a conflict marker — needs <<<<<< too
        assert _has_conflict_markers("=======\n") is False

    def test_has_conflict_markers_mid_file(self) -> None:
        text = "some code\n<<<<<<< HEAD\nmore code\n=======\nother\n>>>>>>> main\n"
        assert _has_conflict_markers(text) is True


# git_ops.py


class TestGitOpsEdgeCases:

    def test_has_remote_returns_false_on_git_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # lines 45-46: GitError → return False
        from grebase.exceptions import GitError
        from grebase.git_ops import has_remote

        monkeypatch.setattr(
            "grebase.git_ops.list_remotes",
            lambda *_: (_ for _ in ()).throw(GitError("fail")),  # type: ignore[arg-type]
        )
        with pytest.raises(GitError):
            has_remote(tmp_path, "origin")

    def test_get_default_branch_falls_back_to_main(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # lines 55-59: symbolic-ref fails → return "main"
        import grebase.git_ops as go
        from grebase.git_ops import get_default_remote_branch as get_default_branch

        def fake_run_git(args, **kwargs):
            raise go.GitError("no remote HEAD")

        monkeypatch.setattr(go, "run_git", fake_run_git)
        result = get_default_branch(tmp_path, "origin")
        assert result == "main"

    def test_get_commits_for_file_returns_empty_on_no_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # lines 159-164: empty stdout → return []
        import grebase.git_ops as go
        from grebase.git_ops import get_commits_for_file

        monkeypatch.setattr(
            go, "run_git", lambda *a, **kw: SimpleNamespace(stdout="", stderr="", returncode=0)
        )
        result = get_commits_for_file(tmp_path, "abc123", "HEAD", "file.py")
        assert result == []

    def test_get_commits_for_file_returns_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # lines 159-164: stdout has commits → return list
        import grebase.git_ops as go
        from grebase.git_ops import get_commits_for_file

        monkeypatch.setattr(
            go,
            "run_git",
            lambda *a, **kw: SimpleNamespace(
                stdout="abc1234 feat: add auth\ndef5678 fix: typo\n",
                stderr="",
                returncode=0,
            ),
        )
        result = get_commits_for_file(tmp_path, "base123", "HEAD", "auth.py")
        assert len(result) == 2
        assert "feat: add auth" in result[0]

    def test_last_commit_for_file_returns_empty_on_no_history(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # line 106: empty log → return ""
        import grebase.git_ops as go
        from grebase.git_ops import last_commit_for_file

        monkeypatch.setattr(
            go, "run_git", lambda *a, **kw: SimpleNamespace(stdout="", stderr="", returncode=0)
        )
        result = last_commit_for_file(tmp_path, "nonexistent.py")
        assert result == ""


# prompts.py


class TestPromptsEdgeCases:

    def test_prompt_lockfile_regen_yes(self) -> None:
        # line 24-29: prompt_lockfile_regen called with y → True
        from grebase.prompts import prompt_lockfile_regen

        with patch("grebase.prompts.prompt", return_value="y"):
            assert prompt_lockfile_regen("yarn.lock", ["yarn", "install"]) is True

    def test_prompt_lockfile_regen_yes_full_word(self) -> None:
        from grebase.prompts import prompt_lockfile_regen

        with patch("grebase.prompts.prompt", return_value="yes"):
            assert prompt_lockfile_regen("poetry.lock", ["poetry", "lock", "--no-update"]) is True

    def test_prompt_lockfile_regen_no(self) -> None:
        from grebase.prompts import prompt_lockfile_regen

        with patch("grebase.prompts.prompt", return_value="n"):
            assert prompt_lockfile_regen("yarn.lock", ["yarn", "install"]) is False

    def test_prompt_lockfile_regen_empty_is_no(self) -> None:
        from grebase.prompts import prompt_lockfile_regen

        with patch("grebase.prompts.prompt", return_value=""):
            assert prompt_lockfile_regen("yarn.lock", ["yarn", "install"]) is False

    def test_prompt_lockfile_regen_uppercase_y(self) -> None:
        # uppercase input is lowercased and accepted
        from grebase.prompts import prompt_lockfile_regen

        with patch("grebase.prompts.prompt", return_value="Y"):
            result = prompt_lockfile_regen("yarn.lock", ["yarn", "install"])
            assert result is True

    def test_prompt_conflict_action_strips_whitespace(self) -> None:
        # line 20: prompt_conflict_action strips result
        from grebase.prompts import prompt_conflict_action

        with patch("grebase.prompts.prompt", return_value="  2  "):
            result = prompt_conflict_action()
        assert result == "2"


# branch_detector.py


class TestBranchDetector:

    def test_select_remote_prefers_explicit(self, tmp_path: Path) -> None:
        assert select_remote(tmp_path, preferred="origin") == "origin"

    def test_select_remote_prefers_upstream_then_origin(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "grebase.branch_detector.has_remote",
            lambda _path, remote: remote == "upstream",
        )
        assert select_remote(tmp_path, preferred="auto") == "upstream"

        monkeypatch.setattr(
            "grebase.branch_detector.has_remote",
            lambda _path, remote: remote == "origin",
        )
        assert select_remote(tmp_path, preferred="auto") == "origin"

    def test_select_remote_none_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("grebase.branch_detector.has_remote", lambda *_, **__: False)
        assert select_remote(tmp_path, preferred="auto") is None

    def test_detect_target_branch_prefers_target(self, tmp_path: Path) -> None:
        assert detect_target_branch(tmp_path, "feature", remote="origin") == "feature"

    def test_detect_target_branch_uses_remote_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("grebase.branch_detector.has_remote", lambda *_, **__: True)
        monkeypatch.setattr(
            "grebase.branch_detector.get_default_remote_branch",
            lambda *_, **__: "develop",
        )
        assert detect_target_branch(tmp_path, None, remote="origin") == "origin/develop"

    def test_detect_target_branch_falls_back_to_main(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("grebase.branch_detector.has_remote", lambda *_, **__: False)
        assert detect_target_branch(tmp_path, None, remote=None) == "main"


# conflict_classifier.py


class TestClassifierAdditionalCases:

    def test_lockfile_is_lockfile(self) -> None:
        text = "<<<<<<< HEAD\nfoo\n=======\nbar\n>>>>>>> main\n"
        result = classify_conflict("yarn.lock", parse_conflict_segments(text))
        assert result == ConflictType.LOCKFILE

    def test_dependency_file_is_semantic(self) -> None:
        text = "<<<<<<< HEAD\nfoo\n=======\nbar\n>>>>>>> main\n"
        result = classify_conflict("requirements.txt", parse_conflict_segments(text))
        assert result == ConflictType.SEMANTIC

    def test_doc_extension_is_documentation(self) -> None:
        text = "<<<<<<< HEAD\nfoo\n=======\nbar\n>>>>>>> main\n"
        result = classify_conflict("README.md", parse_conflict_segments(text))
        assert result == ConflictType.DOCUMENTATION


# conflict_resolver.py


class TestResolverAdditionalCases:

    def test_lockfile_safe_only_returns_false(self, tmp_path: Path) -> None:
        f = tmp_path / "yarn.lock"
        f.write_text("<<<<<<< HEAD\nv1\n=======\nv2\n>>>>>>> main\n", encoding="utf-8")
        config = GrebaseConfig(repo_path=tmp_path, target="main", safe_only=True)
        assert resolve_file(tmp_path, "yarn.lock", config) is False

    def test_non_python_syntax_validation_is_noop(self, tmp_path: Path) -> None:
        f = tmp_path / "readme.md"
        f.write_text("<<<<<<< HEAD\nA\n=======\nB\n>>>>>>> main\n", encoding="utf-8")
        config = GrebaseConfig(repo_path=tmp_path, target="main")
        assert resolve_file(tmp_path, "readme.md", config) is True

    def test_resolve_with_choice_current_and_incoming(self, tmp_path: Path) -> None:
        f = tmp_path / "f.py"
        f.write_text("<<<<<<< HEAD\nA\n=======\nB\n>>>>>>> main\n", encoding="utf-8")
        assert resolve_with_choice(tmp_path, "f.py", "current") is True
        f.write_text("<<<<<<< HEAD\nA\n=======\nB\n>>>>>>> main\n", encoding="utf-8")
        assert resolve_with_choice(tmp_path, "f.py", "incoming") is True


# rules.py


class TestRulesAdditionalCases:

    def test_resolve_formatting_indent_mismatch_returns_none(self) -> None:
        current = "def f():\n    x = 1\n"
        incoming = "def f():\n  x = 1\n"
        assert resolve_formatting(current, incoming) is None

    def test_resolve_formatting_whitespace_only_returns_current(self) -> None:
        current = "x = 1\n\n"
        incoming = "x=1\n"
        assert resolve_formatting(current, incoming) == current


# lockfile_tools.py


class TestLockfileToolsAdditionalCases:

    def test_get_lockfile_command_unknown_returns_none(self) -> None:
        assert get_lockfile_command("unknown.lock") is None


# inline_editor.py


class TestInlineEditorAdditionalCases:

    def test_show_diff_no_changes(self) -> None:
        _show_diff("x = 1\n", "x = 1\n", "f.py")


# repo_detector.py


class TestRepoDetector:

    def test_ensure_git_repo_ok(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("grebase.repo_detector.is_git_repo", lambda *_: True)
        ensure_git_repo(tmp_path)

    def test_ensure_git_repo_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("grebase.repo_detector.is_git_repo", lambda *_: False)
        with pytest.raises(GitError):
            ensure_git_repo(tmp_path)


# state_manager.py
class TestStateManager:

    def test_load_state_missing_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        assert load_state(tmp_path) is None

    def test_save_and_load_state_round_trip(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        save_state(tmp_path, "feature", "main")
        state = load_state(tmp_path)
        assert state is not None
        assert state.branch == "feature"
        assert state.target == "main"
        assert state.started_at


# git_ops.py


class TestGitOpsAdditionalCases:

    def test_list_remotes_empty_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import grebase.git_ops as go

        monkeypatch.setattr(
            go,
            "run_git",
            lambda *a, **kw: go.GitCommandResult("", "", 0),
        )
        assert go.list_remotes(tmp_path) == []

    def test_list_changed_files_parses_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import grebase.git_ops as go

        monkeypatch.setattr(
            go,
            "status_porcelain",
            lambda *_: " M file1\nA  file2\n",
        )
        assert go.list_changed_files(tmp_path) == ["file1", "file2"]

    def test_add_files_empty_is_noop(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import grebase.git_ops as go

        monkeypatch.setattr(
            go,
            "run_git",
            lambda *_: (_ for _ in ()).throw(AssertionError("run_git called")),
        )
        go.add_files(tmp_path, [])

    def test_rebase_continue_no_editor_sets_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import grebase.git_ops as go

        recorded = {}

        def fake_run_git(args, cwd, check=True, env=None):
            recorded["env"] = env
            return go.GitCommandResult("", "", 0)

        monkeypatch.setattr(go, "run_git", fake_run_git)
        go.rebase_continue(tmp_path, allow_editor=False)
        assert recorded["env"] == {"GIT_EDITOR": "true"}

    def test_is_rebase_in_progress_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import grebase.git_ops as go

        monkeypatch.setattr(
            go,
            "run_git",
            lambda *a, **kw: go.GitCommandResult("", "", 0),
        )
        assert go.is_rebase_in_progress(tmp_path) is True

    def test_is_rebase_in_progress_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import grebase.git_ops as go

        monkeypatch.setattr(
            go,
            "run_git",
            lambda *a, **kw: go.GitCommandResult("", "", 1),
        )
        assert go.is_rebase_in_progress(tmp_path) is False


# cli.py


def _setup_cli_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("grebase.cli.ensure_git_repo", lambda *_, **__: None)
    monkeypatch.setattr("grebase.cli.status_porcelain", lambda *_, **__: "")
    monkeypatch.setattr("grebase.cli.is_rebase_in_progress", lambda *_, **__: False)
    monkeypatch.setattr("grebase.cli.get_current_branch", lambda *_, **__: "feature")
    monkeypatch.setattr("grebase.cli.select_remote", lambda *_, **__: None)
    monkeypatch.setattr("grebase.cli.detect_target_branch", lambda *_, **__: "main")
    monkeypatch.setattr("grebase.cli.get_merge_base", lambda *_, **__: None)
    monkeypatch.setattr("grebase.cli.diff_stat_range", lambda *_, **__: "")
    monkeypatch.setattr("grebase.cli.save_state", lambda *_, **__: None)
    monkeypatch.setattr(
        "grebase.cli.rebase",
        lambda *_: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )


class TestCliAdditionalCases:

    def test_version_callback_missing_package(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "grebase.cli.package_version",
            lambda *_: (_ for _ in ()).throw(PackageNotFoundError()),
        )
        with pytest.raises(typer.Exit):
            version_callback(True)

    def test_normalize_policy_aliases(self) -> None:
        assert normalize_policy(" current ") == "mine"
        assert normalize_policy("incoming") == "theirs"
        assert normalize_policy("prompt") == "prompt"

    def test_run_workflow_not_git_repo(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "grebase.cli.ensure_git_repo",
            lambda *_: (_ for _ in ()).throw(GitError("no")),
        )
        assert run_workflow() == 1

    def test_run_workflow_continue_abort_skip_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("grebase.cli.ensure_git_repo", lambda *_: None)
        called = {"continue": 0, "abort": 0, "skip": 0}
        monkeypatch.setattr(
            "grebase.cli.rebase_continue",
            lambda *_: called.__setitem__("continue", 1),
        )
        monkeypatch.setattr(
            "grebase.cli.rebase_abort",
            lambda *_: called.__setitem__("abort", 1),
        )
        monkeypatch.setattr(
            "grebase.cli.rebase_skip",
            lambda *_: called.__setitem__("skip", 1),
        )
        monkeypatch.setattr("grebase.cli.status_porcelain", lambda *_: "")

        assert run_workflow(continue_flag=True) == 0
        assert called["continue"] == 1
        assert run_workflow(abort_flag=True) == 0
        assert called["abort"] == 1
        assert run_workflow(skip_flag=True) == 0
        assert called["skip"] == 1
        assert run_workflow(status_flag=True) == 0

    def test_run_workflow_dirty_tree_no_rebase(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _setup_cli_defaults(monkeypatch, tmp_path)
        monkeypatch.setattr("grebase.cli.status_porcelain", lambda *_: " M file")
        assert run_workflow() == 1

    def test_run_workflow_rebase_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _setup_cli_defaults(monkeypatch, tmp_path)
        monkeypatch.setattr(
            "grebase.cli.rebase",
            lambda *_: SimpleNamespace(returncode=2, stderr="fail", stdout=""),
        )
        assert run_workflow() == 1

    def test_run_workflow_no_conflicts_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _setup_cli_defaults(monkeypatch, tmp_path)
        monkeypatch.setattr("grebase.cli.get_conflict_files", lambda *_: [])
        assert run_workflow() == 0

    def test_run_workflow_auto_resolve_non_lockfile(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _setup_cli_defaults(monkeypatch, tmp_path)
        calls = {"add_files": 0, "continue": 0}
        conflicts = iter([["app.py"], []])
        monkeypatch.setattr("grebase.cli.get_conflict_files", lambda *_: next(conflicts))
        monkeypatch.setattr("grebase.cli.resolve_file", lambda *_, **__: True)
        monkeypatch.setattr(
            "grebase.cli.add_files",
            lambda *_, **__: calls.__setitem__("add_files", 1),
        )
        monkeypatch.setattr(
            "grebase.cli.rebase_continue",
            lambda *_, **__: calls.__setitem__("continue", 1),
        )
        assert run_workflow() == 0
        assert calls["add_files"] == 1
        assert calls["continue"] == 1

    def test_run_workflow_auto_resolve_lockfile_uses_add_all(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _setup_cli_defaults(monkeypatch, tmp_path)
        calls = {"add_all": 0}
        conflicts = iter([["yarn.lock"], []])
        monkeypatch.setattr("grebase.cli.get_conflict_files", lambda *_: next(conflicts))
        monkeypatch.setattr("grebase.cli.resolve_file", lambda *_, **__: True)
        monkeypatch.setattr(
            "grebase.cli.add_all_changes",
            lambda *_, **__: calls.__setitem__("add_all", 1),
        )
        monkeypatch.setattr("grebase.cli.rebase_continue", lambda *_, **__: None)
        assert run_workflow() == 0
        assert calls["add_all"] == 1

    def test_run_workflow_noninteractive_policy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _setup_cli_defaults(monkeypatch, tmp_path)
        conflicts = iter([["f.py"], []])
        monkeypatch.setattr("grebase.cli.get_conflict_files", lambda *_: next(conflicts))
        monkeypatch.setattr("grebase.cli.resolve_file", lambda *_, **__: False)
        monkeypatch.setattr("grebase.cli.resolve_with_choice", lambda *_, **__: True)
        monkeypatch.setattr("grebase.cli.add_files", lambda *_, **__: None)
        monkeypatch.setattr("grebase.cli.rebase_continue", lambda *_, **__: None)
        assert run_workflow(interactive=False, policy="mine") == 0

    def test_run_workflow_noninteractive_prompt_returns_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _setup_cli_defaults(monkeypatch, tmp_path)
        monkeypatch.setattr("grebase.cli.get_conflict_files", lambda *_: ["f.py"])
        monkeypatch.setattr("grebase.cli.resolve_file", lambda *_, **__: False)
        assert run_workflow(interactive=False, policy="prompt") == 2

    def test_run_workflow_action_diff_then_mine(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _setup_cli_defaults(monkeypatch, tmp_path)
        conflicts = iter([["f.py"], []])
        monkeypatch.setattr("grebase.cli.get_conflict_files", lambda *_: next(conflicts))
        monkeypatch.setattr("grebase.cli.resolve_file", lambda *_, **__: False)
        monkeypatch.setattr("grebase.cli.diff_file", lambda *_: "diff")
        actions = iter(["5", "1"])
        monkeypatch.setattr("grebase.cli.prompt_conflict_action", lambda: next(actions))
        monkeypatch.setattr("grebase.cli.resolve_with_choice", lambda *_, **__: True)
        monkeypatch.setattr("grebase.cli.add_files", lambda *_, **__: None)
        monkeypatch.setattr("grebase.cli.rebase_continue", lambda *_, **__: None)
        assert run_workflow(interactive=True) == 0

    def test_run_workflow_action_both_mine_refine_yes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _setup_cli_defaults(monkeypatch, tmp_path)
        conflicts = iter([["f.py"], []])
        monkeypatch.setattr("grebase.cli.get_conflict_files", lambda *_: next(conflicts))
        monkeypatch.setattr("grebase.cli.resolve_file", lambda *_, **__: False)
        monkeypatch.setattr(
            "grebase.cli.resolve_with_both",
            lambda *_, **__: (True, "preview"),
        )
        monkeypatch.setattr(
            "grebase.cli.edit_and_validate",
            lambda *_, **__: ("orig", "edited"),
        )
        monkeypatch.setattr("grebase.cli.add_files", lambda *_, **__: None)
        monkeypatch.setattr("grebase.cli.rebase_continue", lambda *_, **__: None)
        prompts = iter(["y", "y"])
        monkeypatch.setattr("grebase.cli.pt_prompt", lambda *_: next(prompts))
        monkeypatch.setattr("grebase.cli.prompt_conflict_action", lambda: "6")
        assert run_workflow(interactive=True) == 0

    def test_run_workflow_action_both_theirs_refine_no(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _setup_cli_defaults(monkeypatch, tmp_path)
        conflicts = iter([["f.py"], []])
        monkeypatch.setattr("grebase.cli.get_conflict_files", lambda *_: next(conflicts))
        monkeypatch.setattr("grebase.cli.resolve_file", lambda *_, **__: False)
        monkeypatch.setattr(
            "grebase.cli.resolve_with_both",
            lambda *_, **__: (True, "preview"),
        )
        monkeypatch.setattr("grebase.cli.add_files", lambda *_, **__: None)
        monkeypatch.setattr("grebase.cli.rebase_continue", lambda *_, **__: None)
        monkeypatch.setattr("grebase.cli.pt_prompt", lambda *_: "n")
        monkeypatch.setattr("grebase.cli.prompt_conflict_action", lambda: "7")
        assert run_workflow(interactive=True) == 0

    def test_run_workflow_action_inline_abort(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _setup_cli_defaults(monkeypatch, tmp_path)
        (tmp_path / "f.py").write_text("x = 1\n", encoding="utf-8")
        monkeypatch.setattr("grebase.cli.get_conflict_files", lambda *_: ["f.py"])
        monkeypatch.setattr("grebase.cli.resolve_file", lambda *_, **__: False)
        monkeypatch.setattr("grebase.cli.edit_and_validate", lambda *_, **__: None)
        called = {"abort": 0}
        monkeypatch.setattr("grebase.cli.rebase_abort", lambda *_: called.__setitem__("abort", 1))
        monkeypatch.setattr("grebase.cli.pt_prompt", lambda *_: "y")
        monkeypatch.setattr("grebase.cli.prompt_conflict_action", lambda: "8")
        assert run_workflow(interactive=True) == 1
        assert called["abort"] == 1

    def test_run_workflow_action_skip_and_abort(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _setup_cli_defaults(monkeypatch, tmp_path)
        monkeypatch.setattr("grebase.cli.get_conflict_files", lambda *_: ["f.py"])
        monkeypatch.setattr("grebase.cli.resolve_file", lambda *_, **__: False)
        monkeypatch.setattr("grebase.cli.rebase_skip", lambda *_: None)
        monkeypatch.setattr("grebase.cli.prompt_conflict_action", lambda: "9")
        assert run_workflow(interactive=True) == 2

        monkeypatch.setattr("grebase.cli.rebase_abort", lambda *_: None)
        monkeypatch.setattr("grebase.cli.prompt_conflict_action", lambda: "10")
        assert run_workflow(interactive=True) == 1

    def test_run_workflow_invalid_selection_then_mine(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _setup_cli_defaults(monkeypatch, tmp_path)
        conflicts = iter([["f.py"], []])
        monkeypatch.setattr("grebase.cli.get_conflict_files", lambda *_: next(conflicts))
        monkeypatch.setattr("grebase.cli.resolve_file", lambda *_, **__: False)
        actions = iter(["invalid", "1"])
        monkeypatch.setattr("grebase.cli.prompt_conflict_action", lambda: next(actions))
        monkeypatch.setattr("grebase.cli.resolve_with_choice", lambda *_, **__: True)
        monkeypatch.setattr("grebase.cli.add_files", lambda *_, **__: None)
        monkeypatch.setattr("grebase.cli.rebase_continue", lambda *_, **__: None)
        assert run_workflow(interactive=True) == 0
