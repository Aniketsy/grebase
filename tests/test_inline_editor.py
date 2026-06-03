from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from grebase.inline_editor import _has_conflict_markers, _show_diff, edit_and_validate, inline_edit


def test_has_conflict_markers_true() -> None:
    assert _has_conflict_markers("<<<<<<< HEAD\nx=1\n=======\nx=2\n>>>>>>> main") is True


def test_has_conflict_markers_false() -> None:
    assert _has_conflict_markers("x = 1\ny = 2\n") is False


def test_edit_and_validate_clean_input(tmp_path: Path) -> None:
    f = tmp_path / "f.py"
    f.write_text("x = 1\n", encoding="utf-8")
    with patch("grebase.inline_editor.inline_edit", return_value="x = 2\n"):
        result = edit_and_validate(f)
    assert result is not None
    original, edited = result
    assert original == "x = 1\n"
    assert edited == "x = 2\n"


def test_edit_and_validate_aborted(tmp_path: Path) -> None:
    f = tmp_path / "f.py"
    f.write_text("x = 1\n", encoding="utf-8")
    with patch("grebase.inline_editor.inline_edit", return_value=None):
        result = edit_and_validate(f)
    assert result is None


def test_edit_and_validate_retries_on_conflict_markers(tmp_path: Path) -> None:
    f = tmp_path / "f.py"
    f.write_text("x = 1\n", encoding="utf-8")
    with patch(
        "grebase.inline_editor.inline_edit",
        side_effect=[
            "<<<<<<< HEAD\nx=1\n=======\nx=2\n>>>>>>> main\n",
            "x = 2\n",
        ],
    ):
        result = edit_and_validate(f)
    assert result is not None
    _, edited = result
    assert edited == "x = 2\n"


def test_edit_and_validate_retries_on_empty(tmp_path: Path) -> None:
    f = tmp_path / "f.py"
    f.write_text("x = 1\n", encoding="utf-8")
    with patch(
        "grebase.inline_editor.inline_edit",
        side_effect=["   \n", "x = 2\n"],
    ):
        result = edit_and_validate(f)
    assert result is not None
    _, edited = result
    assert edited == "x = 2\n"


def test_show_diff_no_changes(tmp_path: Path) -> None:
    _show_diff("x = 1\n", "x = 1\n", "f.py")


def test_inline_edit_eoferror_returns_none(tmp_path: Path) -> None:
    file_path = tmp_path / "f.py"
    file_path.write_text("x = 1\n", encoding="utf-8")
    with patch("grebase.inline_editor.prompt", side_effect=EOFError):
        assert inline_edit(file_path) is None


def test_inline_edit_uses_wrap_lines_true(tmp_path: Path) -> None:
    file_path = tmp_path / "f.py"
    file_path.write_text("x = 1\n", encoding="utf-8")
    with patch("grebase.inline_editor.prompt", return_value="x = 2\n") as mocked:
        inline_edit(file_path)
    _, kwargs = mocked.call_args
    assert kwargs["wrap_lines"] is True
