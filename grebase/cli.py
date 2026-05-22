from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .branch_detector import detect_target_branch, select_remote
from .config import GrebaseConfig
from .conflict_classifier import LOCKFILES
from .conflict_detector import get_conflict_files
from .conflict_resolver import resolve_file, resolve_with_choice
from .exceptions import GitError
from .git_ops import (
    add_all_changes,
    add_files,
    diff_file,
    diff_stat_range,
    fetch,
    get_current_branch,
    has_remote,
    is_rebase_in_progress,
    last_commit_for_file,
    rebase,
    rebase_abort,
    rebase_continue,
    rebase_skip,
    status_porcelain,
)
from .logger import get_logger
from .prompts import prompt_conflict_action
from .repo_detector import ensure_git_repo
from .state_manager import save_state

app = typer.Typer(add_completion=False, help="grebase - safe Git rebase assistant")
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    target: Optional[str] = typer.Argument(None),
    continue_flag: bool = typer.Option(False, "--continue"),
    abort_flag: bool = typer.Option(False, "--abort"),
    skip_flag: bool = typer.Option(False, "--skip"),
    status_flag: bool = typer.Option(False, "--status"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    interactive: bool = typer.Option(
        True,
        "--interactive/--non-interactive",
        help="Prompt for unresolved conflicts (default: on)",
    ),
    safe_only: bool = typer.Option(False, "--safe-only"),
    remote: str = typer.Option(
        "auto",
        "--remote",
        help="Remote to rebase against (auto|origin|upstream|<name>)",
    ),
    policy: str = typer.Option(
        "prompt",
        "--policy",
        help="Ambiguous conflict policy: prompt, current, incoming",
    ),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    if ctx.invoked_subcommand is None:
        ctx.invoke(
            run,
            target=target,
            continue_flag=continue_flag,
            abort_flag=abort_flag,
            skip_flag=skip_flag,
            status_flag=status_flag,
            dry_run=dry_run,
            interactive=interactive,
            safe_only=safe_only,
            remote=remote,
            policy=policy,
            verbose=verbose,
        )


def run_workflow(
    target: Optional[str] = None,
    continue_flag: bool = False,
    abort_flag: bool = False,
    skip_flag: bool = False,
    status_flag: bool = False,
    dry_run: bool = False,
    interactive: bool = True,
    safe_only: bool = False,
    remote: str = "auto",
    policy: str = "prompt",
    verbose: bool = False,
) -> int:
    repo_path = Path.cwd()
    logger = get_logger("grebase", verbose=verbose)

    try:
        ensure_git_repo(repo_path)
    except GitError as exc:
        console.print(f"[red]x[/red] {exc}")
        return 1

    if continue_flag:
        rebase_continue(repo_path)
        console.print("[green]✓[/green] Rebase continued")
        return 0
    if abort_flag:
        rebase_abort(repo_path)
        console.print("[yellow]![/yellow] Rebase aborted")
        return 0
    if skip_flag:
        rebase_skip(repo_path)
        console.print("[yellow]![/yellow] Rebase skipped")
        return 0
    if status_flag:
        console.print(status_porcelain(repo_path) or "clean")
        return 0

    rebase_in_progress = is_rebase_in_progress(repo_path)

    if status_porcelain(repo_path) and not rebase_in_progress:
        console.print(
            "[yellow]![/yellow] Working tree not clean. Commit or stash changes first."
        )
        return 1

    current_branch = get_current_branch(repo_path)
    selected_remote = select_remote(repo_path, preferred=remote)
    target_branch = detect_target_branch(repo_path, target, remote=selected_remote)
    config = GrebaseConfig(
        repo_path=repo_path,
        target=target_branch,
        dry_run=dry_run,
        interactive=interactive,
        safe_only=safe_only,
        verbose=verbose,
    )

    console.print("[green]✓[/green] Repository detected")
    console.print(f"[green]✓[/green] Current branch: {current_branch}")
    console.print(f"[green]✓[/green] Target branch: {target_branch}")
    if selected_remote:
        console.print(f"[green]✓[/green] Remote: {selected_remote}")

    summary = diff_stat_range(repo_path, target_branch)
    if summary:
        console.print("[blue]i[/blue] Incoming changes summary:")
        console.print(summary)

    if rebase_in_progress:
        console.print("[yellow]![/yellow] Resuming rebase with conflicts")
    elif config.dry_run:
        console.print("[yellow]![/yellow] Dry run - skipping fetch")
    elif selected_remote and has_remote(repo_path, remote=selected_remote):
        fetch(repo_path, remote=selected_remote)
        console.print("[green]✓[/green] Fetch completed")
    else:
        console.print("[yellow]![/yellow] No remote found - skipping fetch")

    if not rebase_in_progress:
        save_state(repo_path, current_branch, target_branch)

    if not config.dry_run and not rebase_in_progress:
        rebase(repo_path, target_branch)

    batch_choice: str | None = None
    while True:
        conflict_files = get_conflict_files(repo_path)
        if not conflict_files:
            console.print("[green]✓[/green] Rebase successful")
            return 0

        resolved_files: list[str] = []
        for conflict_file in conflict_files:
            logger.debug("attempting auto-resolve: %s", conflict_file)
            resolved = resolve_file(repo_path, conflict_file, config)
            if resolved:
                resolved_files.append(conflict_file)
                console.print(f"[green]✓[/green] Auto-resolved {conflict_file}")
                continue

            if not config.interactive and policy != "prompt":
                resolve_with_choice(repo_path, conflict_file, policy)
                resolved_files.append(conflict_file)
                console.print(
                    f"[green]✓[/green] Applied {policy} to {conflict_file}"
                )
                continue

            if not config.interactive:
                console.print(
                    f"[yellow]![/yellow] Conflict requires input: {conflict_file}"
                )
                return 2

            last_commit = last_commit_for_file(repo_path, conflict_file)
            console.print(f"[yellow]![/yellow] Conflict: {conflict_file}")
            if last_commit:
                console.print(f"[blue]i[/blue] Last change: {last_commit}")
            console.print(
                "[blue]i[/blue] Choose how to resolve. If unsure, use Show diff."
            )

            action = batch_choice or prompt_conflict_action()
            if action == "1":
                resolve_with_choice(repo_path, conflict_file, "current")
                resolved_files.append(conflict_file)
            elif action == "2":
                resolve_with_choice(repo_path, conflict_file, "incoming")
                resolved_files.append(conflict_file)
            elif action == "3":
                batch_choice = "3"
                resolve_with_choice(repo_path, conflict_file, "current")
                resolved_files.append(conflict_file)
            elif action == "4":
                batch_choice = "4"
                resolve_with_choice(repo_path, conflict_file, "incoming")
                resolved_files.append(conflict_file)
            elif action == "5":
                console.print(diff_file(repo_path, conflict_file))
                return 2
            elif action == "6":
                rebase_skip(repo_path)
                return 2
            elif action == "7":
                rebase_abort(repo_path)
                return 1
            else:
                console.print("Invalid selection")
                return 2

        if resolved_files and not config.dry_run:
            if any(Path(path).name in LOCKFILES for path in resolved_files):
                add_all_changes(repo_path)
            else:
                add_files(repo_path, resolved_files)
            rebase_continue(repo_path, allow_editor=config.interactive)

    return 0


@app.command("run")
def run(
    target: Optional[str] = typer.Argument(None),
    continue_flag: bool = typer.Option(False, "--continue"),
    abort_flag: bool = typer.Option(False, "--abort"),
    skip_flag: bool = typer.Option(False, "--skip"),
    status_flag: bool = typer.Option(False, "--status"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    interactive: bool = typer.Option(
        True,
        "--interactive/--non-interactive",
        help="Prompt for unresolved conflicts (default: on)",
    ),
    safe_only: bool = typer.Option(False, "--safe-only"),
    remote: str = typer.Option(
        "auto",
        "--remote",
        help="Remote to rebase against (auto|origin|upstream|<name>)",
    ),
    policy: str = typer.Option(
        "prompt",
        "--policy",
        help="Ambiguous conflict policy: prompt, current, incoming",
    ),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    exit_code = run_workflow(
        target=target,
        continue_flag=continue_flag,
        abort_flag=abort_flag,
        skip_flag=skip_flag,
        status_flag=status_flag,
        dry_run=dry_run,
        interactive=interactive,
        safe_only=safe_only,
        remote=remote,
        policy=policy,
        verbose=verbose,
    )
    raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
