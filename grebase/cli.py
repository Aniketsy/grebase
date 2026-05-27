from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Optional

import typer
from prompt_toolkit import prompt as pt_prompt
from rich.console import Console

from .audit_log import append_audit
from .branch_detector import detect_target_branch, select_remote
from .config import GrebaseConfig
from .conflict_classifier import LOCKFILES
from .conflict_detector import get_conflict_files
from .conflict_resolver import resolve_file, resolve_with_both, resolve_with_choice
from .exceptions import GitError
from .git_ops import (
    add_all_changes,
    add_files,
    diff_file,
    diff_stat_range,
    fetch,
    get_commits_for_file,
    get_current_branch,
    get_file_at_commit,
    get_merge_base,
    has_remote,
    is_rebase_in_progress,
    last_commit_for_file,
    rebase,
    rebase_abort,
    rebase_continue,
    rebase_skip,
    status_porcelain,
)
from .inline_editor import edit_and_validate
from .logger import get_logger
from .prompts import prompt_conflict_action
from .repo_detector import ensure_git_repo
from .state_manager import save_state

app = typer.Typer(add_completion=False, help="grebase - safe Git rebase assistant")
console = Console()


def version_callback(value: bool) -> None:
    if value:
        try:
            resolved_version = package_version("grebase")
        except PackageNotFoundError:
            resolved_version = "0.0.0"
        console.print(f"grebase {resolved_version}")
        raise typer.Exit()


def normalize_policy(policy: str) -> str:
    normalized = policy.strip().lower()
    if normalized in {"current", "mine"}:
        return "mine"
    if normalized in {"incoming", "theirs"}:
        return "theirs"
    return normalized


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    target: Optional[str] = typer.Argument(None),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show grebase version and exit",
    ),
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
        help=(
            "Ambiguous conflict policy: prompt, mine (yours), theirs (target). "
            "Aliases: current=mine, incoming=theirs"
        ),
    ),
    audit: bool = typer.Option(False, "--audit", help="Write audit log to .git/grebase.log"),
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
            audit=audit,
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
    audit: bool = False,
    verbose: bool = False,
) -> int:
    repo_path = Path.cwd()
    logger = get_logger("grebase", verbose=verbose)
    normalized_policy = normalize_policy(policy)

    try:
        ensure_git_repo(repo_path)
    except GitError as exc:
        console.print(f"[red]x[/red] {exc}")
        return 1

    def audit_log(action: str, detail: str) -> None:
        if audit:
            append_audit(repo_path, action, detail)

    def _edit_loop(
        conflict_file: str,
        resolved_files: list[str],
        initial_content: str | None = None,
        header: str | None = None,
    ) -> str:
        """
        Open inline terminal editor, validate, confirm, stage.
        Returns "continue" or "abort".
        """
        file_path = repo_path / conflict_file
        result = edit_and_validate(
            file_path,
            initial_content=initial_content,
            header=header,
        )
        if result is None:
            console.print("[yellow]![/yellow] Aborting rebase.")
            rebase_abort(repo_path)
            return "abort"

        _, edited = result
        file_path.write_text(edited, encoding="utf-8")

        try:
            answer = pt_prompt("  Stage this file and continue? [Y/n] ").strip().lower()
        except KeyboardInterrupt:
            rebase_abort(repo_path)
            return "abort"

        if answer in {"n", "no"}:
            console.print("[yellow]![/yellow] Aborting rebase.")
            rebase_abort(repo_path)
            return "abort"

        resolved_files.append(conflict_file)
        audit_log("choice", f"manual-edit {conflict_file}")
        return "continue"

    if continue_flag:
        try:
            rebase_continue(repo_path)
        except GitError as exc:
            console.print(f"[red]x[/red] {exc}")
            return 1
        console.print("[green]✓[/green] Rebase continued")
        audit_log("continue", "rebase --continue")
        return 0
    if abort_flag:
        try:
            rebase_abort(repo_path)
        except GitError as exc:
            console.print(f"[red]x[/red] {exc}")
            return 1
        console.print("[yellow]![/yellow] Rebase aborted")
        audit_log("abort", "rebase --abort")
        return 0
    if skip_flag:
        try:
            rebase_skip(repo_path)
        except GitError as exc:
            console.print(f"[red]x[/red] {exc}")
            return 1
        console.print("[yellow]![/yellow] Rebase skipped")
        audit_log("skip", "rebase --skip")
        return 0
    if status_flag:
        console.print(status_porcelain(repo_path) or "clean")
        return 0

    rebase_in_progress = is_rebase_in_progress(repo_path)

    status_output = status_porcelain(repo_path)
    dirty_lines = [line for line in status_output.splitlines() if not line.startswith("??")]
    if dirty_lines and not rebase_in_progress:
        console.print("[yellow]![/yellow] Working tree not clean. Commit or stash changes first.")
        return 1

    current_branch = get_current_branch(repo_path)
    selected_remote = select_remote(repo_path, preferred=remote)
    target_branch = detect_target_branch(repo_path, target, remote=selected_remote)
    merge_base_sha = get_merge_base(repo_path, target_branch)
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
        audit_log("target", f"remote={selected_remote} target={target_branch}")
    else:
        audit_log("target", f"target={target_branch}")

    summary = diff_stat_range(repo_path, target_branch)
    if summary:
        console.print("[blue]i[/blue] Incoming changes summary:")
        console.print(summary)

    if rebase_in_progress:
        console.print("[yellow]![/yellow] Resuming rebase with conflicts")
        audit_log("resume", "rebase in progress")
    elif config.dry_run:
        console.print("[yellow]![/yellow] Dry run - skipping fetch")
        audit_log("dry-run", "skip fetch/rebase")
    elif selected_remote and has_remote(repo_path, remote=selected_remote):
        fetch(repo_path, remote=selected_remote)
        console.print("[green]✓[/green] Fetch completed")
        audit_log("fetch", f"remote={selected_remote}")
    else:
        console.print("[yellow]![/yellow] No remote found - skipping fetch")
        audit_log("fetch", "skipped (no remote)")

    if not rebase_in_progress:
        save_state(repo_path, current_branch, target_branch)

    if not config.dry_run and not rebase_in_progress:
        result = rebase(repo_path, target_branch)
        audit_log("rebase", f"target={target_branch}")
        if result.returncode not in (0, 1):
            error_detail = result.stderr or "git rebase failed"
            console.print(f"[red]x[/red] git rebase failed: {error_detail}")
            return 1

    batch_choice: str | None = None
    while True:
        conflict_files = get_conflict_files(repo_path)
        if not conflict_files:
            console.print("[green]✓[/green] Rebase successful")
            audit_log("success", "rebase completed")
            return 0

        resolved_files: list[str] = []
        for conflict_file in conflict_files:
            logger.debug("attempting auto-resolve: %s", conflict_file)
            base_content = None
            if merge_base_sha:
                base_content = get_file_at_commit(repo_path, merge_base_sha, conflict_file)
            resolved = resolve_file(
                repo_path,
                conflict_file,
                config,
                base_content=base_content,
            )
            if resolved:
                resolved_files.append(conflict_file)
                console.print(f"[green]✓[/green] Auto-resolved {conflict_file}")
                audit_log("auto-resolve", conflict_file)
                continue

            if not config.interactive and normalized_policy != "prompt":
                resolve_with_choice(repo_path, conflict_file, normalized_policy)
                resolved_files.append(conflict_file)
                console.print(f"[green]✓[/green] Applied {normalized_policy} to {conflict_file}")
                audit_log("policy", f"{normalized_policy} {conflict_file}")
                continue

            if not config.interactive:
                console.print(f"[yellow]![/yellow] Conflict requires input: {conflict_file}")
                return 2

            last_commit = last_commit_for_file(repo_path, conflict_file)
            console.print(f"[yellow]![/yellow] Conflict: {conflict_file}")
            if merge_base_sha:
                commits = get_commits_for_file(
                    repo_path,
                    merge_base_sha,
                    "HEAD",
                    conflict_file,
                )
                if commits:
                    console.print("[blue]◆[/blue] Commits that changed this file:")
                    for commit_line in commits:
                        console.print(f"  [dim]{commit_line}[/dim]")
            if last_commit:
                console.print(f"[blue]i[/blue] Last change: {last_commit}")
            console.print("[blue]i[/blue] Choose how to resolve. If unsure, use Show diff.")

            while True:
                action: str | None = None
                if batch_choice == "mine":
                    action = "3"
                elif batch_choice == "theirs":
                    action = "4"
                if action is None:
                    action = prompt_conflict_action()
                if action == "1":
                    resolve_with_choice(repo_path, conflict_file, "mine")
                    resolved_files.append(conflict_file)
                    audit_log("choice", f"mine {conflict_file}")
                    break
                if action == "2":
                    resolve_with_choice(repo_path, conflict_file, "theirs")
                    resolved_files.append(conflict_file)
                    audit_log("choice", f"theirs {conflict_file}")
                    break
                if action == "3":
                    batch_choice = "mine"
                    resolve_with_choice(repo_path, conflict_file, "mine")
                    resolved_files.append(conflict_file)
                    audit_log("choice", f"mine-all {conflict_file}")
                    break
                if action == "4":
                    batch_choice = "theirs"
                    resolve_with_choice(repo_path, conflict_file, "theirs")
                    resolved_files.append(conflict_file)
                    audit_log("choice", f"theirs-all {conflict_file}")
                    break
                if action == "5":
                    console.print(diff_file(repo_path, conflict_file))
                    audit_log("diff", conflict_file)
                    continue
                if action == "6":
                    _, preview = resolve_with_both(repo_path, conflict_file, mine_first=True)
                    console.print("[blue]◆[/blue] Both sides merged - mine first.")
                    refine = pt_prompt("  Refine inline? [y/N] ").strip().lower()
                    if refine in {"y", "yes"}:
                        outcome = _edit_loop(
                            conflict_file,
                            resolved_files,
                            initial_content=preview,
                            header=f"Refining: {conflict_file} (both sides - mine first)",
                        )
                        if outcome == "abort":
                            return 1
                    else:
                        resolved_files.append(conflict_file)
                        audit_log("choice", f"both-mine-first {conflict_file}")
                    break
                if action == "7":
                    _, preview = resolve_with_both(repo_path, conflict_file, mine_first=False)
                    console.print("[blue]◆[/blue] Both sides merged - theirs first.")
                    refine = pt_prompt("  Refine inline? [y/N] ").strip().lower()
                    if refine in {"y", "yes"}:
                        outcome = _edit_loop(
                            conflict_file,
                            resolved_files,
                            initial_content=preview,
                            header=f"Refining: {conflict_file} (both sides - theirs first)",
                        )
                        if outcome == "abort":
                            return 1
                    else:
                        resolved_files.append(conflict_file)
                        audit_log("choice", f"both-theirs-first {conflict_file}")
                    break
                if action == "8":
                    current = (repo_path / conflict_file).read_text(
                        encoding="utf-8", errors="replace"
                    )
                    outcome = _edit_loop(
                        conflict_file,
                        resolved_files,
                        initial_content=current,
                        header=f"Editing: {conflict_file} (resolve manually)",
                    )
                    if outcome == "abort":
                        return 1
                    break
                if action == "9":
                    # Guarded by git_ops; this path only runs during an active rebase.
                    rebase_skip(repo_path)
                    audit_log("skip", "rebase --skip")
                    return 2
                if action == "10":
                    # Guarded by git_ops; this path only runs during an active rebase.
                    rebase_abort(repo_path)
                    audit_log("abort", "rebase --abort")
                    return 1
                console.print("Invalid selection")

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
        help=(
            "Ambiguous conflict policy: prompt, mine (yours), theirs (target). "
            "Aliases: current=mine, incoming=theirs"
        ),
    ),
    audit: bool = typer.Option(False, "--audit", help="Write audit log to .git/grebase.log"),
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
        audit=audit,
        verbose=verbose,
    )
    raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
