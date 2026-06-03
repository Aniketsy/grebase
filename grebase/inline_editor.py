from __future__ import annotations

import difflib
from pathlib import Path

from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.styles import Style
from rich.console import Console

console = Console()

_STYLE = Style.from_dict(
    {
        "bottom-toolbar": "bg:#1a1d21 #484f58",
        "bottom-toolbar.text": "bg:#1a1d21 #79c0ff",
    }
)

_TOOLBAR = HTML(
    "<b>Ctrl+D</b> save  "
    "<b>Ctrl+C</b> abort  "
    "<b>Enter</b> new line  "
    "<b>Arrows</b> navigate"
)


def _has_conflict_markers(text: str) -> bool:
    return "<<<<<<<" in text


def _make_keybindings() -> KeyBindings:
    kb = KeyBindings()

    @kb.add("c-d")
    def _submit(event: KeyPressEvent) -> None:
        """Ctrl+D - submit the edit."""
        event.app.exit(result=event.app.current_buffer.text)

    return kb


def inline_edit(
    file_path: Path,
    initial_content: str | None = None,
    header: str | None = None,
) -> str | None:
    """
    Open an inline multi-line editor in the terminal pre-populated
    with initial_content (or the file's current content).

    Returns the edited text on save, or None if the user aborted.
    """
    content = (
        initial_content
        if initial_content is not None
        else file_path.read_text(encoding="utf-8", errors="replace")
    )

    label = header or f"Editing: {file_path.name}"
    console.print(f"\n[blue]◆[/blue] {label}")
    console.print(
        "[dim]  Ctrl+D to save  ·  Ctrl+C to abort  ·  "
        "Enter for new line  ·  Arrow keys to navigate[/dim]"
    )
    console.print("-" * 60)

    try:
        result = prompt(
            "",
            default=content,
            multiline=True,
            key_bindings=_make_keybindings(),
            bottom_toolbar=_TOOLBAR,
            style=_STYLE,
            wrap_lines=True,
        )
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]![/yellow] Edit aborted.")
        return None

    console.print("-" * 60)
    return result


def edit_and_validate(
    file_path: Path,
    initial_content: str | None = None,
    header: str | None = None,
) -> tuple[str, str] | None:
    """
    Open inline editor, validate the result, loop until clean.
    Returns (original_content, edited_content) or None if aborted.
    """
    original = file_path.read_text(encoding="utf-8", errors="replace")
    current_content = initial_content if initial_content is not None else original

    while True:
        edited = inline_edit(file_path, current_content, header)

        if edited is None:
            return None

        if not edited.strip():
            console.print(
                "[red]x[/red] File is empty - did you delete everything? " "Re-opening editor."
            )
            current_content = edited
            continue

        if _has_conflict_markers(edited):
            console.print(
                "[red]x[/red] Conflict markers still present (<<<<<<< found). " "Re-opening editor."
            )
            current_content = edited
            continue

        _show_diff(original, edited, file_path.name)
        return original, edited


def _show_diff(original: str, edited: str, filename: str) -> None:
    """Show a compact diff of what the user changed."""
    orig_lines = original.splitlines(keepends=True)
    edit_lines = edited.splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            orig_lines,
            edit_lines,
            fromfile=f"{filename} (before)",
            tofile=f"{filename} (after)",
            n=2,
        )
    )
    if not diff:
        console.print("[dim]  No changes made.[/dim]")
        return
    console.print("\n[blue]◆[/blue] Changes you made:")
    for line in diff[2:]:
        line = line.rstrip("\n")
        if line.startswith("+"):
            console.print(f"  [green]{line}[/green]")
        elif line.startswith("-"):
            console.print(f"  [red]{line}[/red]")
        else:
            console.print(f"  [dim]{line}[/dim]")
