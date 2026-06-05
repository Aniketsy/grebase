from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .exceptions import GitError


@dataclass(frozen=True)
class GitCommandResult:
    stdout: str
    stderr: str
    returncode: int


def run_git(
    args: Iterable[str],
    cwd: Path,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> GitCommandResult:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env=merged_env,
    )
    if check and result.returncode != 0:
        raise GitError(result.stderr.strip() or "git command failed")
    return GitCommandResult(result.stdout.strip(), result.stderr.strip(), result.returncode)


def is_git_repo(repo_path: Path) -> bool:
    try:
        run_git(["rev-parse", "--git-dir"], cwd=repo_path, check=True)
        return True
    except GitError:
        return False


def get_current_branch(repo_path: Path) -> str:
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    return result.stdout


def get_default_remote_branch(repo_path: Path, remote: str = "origin") -> str:
    try:
        result = run_git(["symbolic-ref", f"refs/remotes/{remote}/HEAD"], cwd=repo_path)
        return result.stdout.replace(f"refs/remotes/{remote}/", "")
    except GitError:
        pass

    for branch in ("master", "main"):
        result = run_git(
            ["ls-remote", "--heads", remote, branch],
            cwd=repo_path,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return branch

    return "main"


def fetch(repo_path: Path, remote: str = "origin") -> None:
    run_git(["fetch", remote], cwd=repo_path)


def list_remotes(repo_path: Path) -> list[str]:
    result = run_git(["remote"], cwd=repo_path)
    if not result.stdout:
        return []
    return result.stdout.splitlines()


def has_remote(repo_path: Path, remote: str = "origin") -> bool:
    return remote in list_remotes(repo_path)


def rebase(repo_path: Path, target: str) -> GitCommandResult:
    return run_git(["rebase", target], cwd=repo_path, check=False)


def rebase_continue(repo_path: Path, allow_editor: bool = True) -> GitCommandResult:
    if not is_rebase_in_progress(repo_path):
        raise GitError("No rebase in progress. Run `grebase <target>` to start one.")
    env = None if allow_editor else {"GIT_EDITOR": "true"}
    # check=False: returncode 1 is expected when the next commit has conflicts.
    return run_git(["rebase", "--continue"], cwd=repo_path, env=env, check=False)


def rebase_abort(repo_path: Path) -> None:
    if not is_rebase_in_progress(repo_path):
        raise GitError("No rebase in progress. Run `grebase <target>` to start one.")
    run_git(["rebase", "--abort"], cwd=repo_path)


def rebase_skip(repo_path: Path) -> None:
    if not is_rebase_in_progress(repo_path):
        raise GitError("No rebase in progress. Run `grebase <target>` to start one.")
    run_git(["rebase", "--skip"], cwd=repo_path)


def is_rebase_in_progress(repo_path: Path) -> bool:
    git_dir = repo_path / ".git"
    return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()


def status_porcelain(repo_path: Path) -> str:
    return run_git(["status", "--porcelain"], cwd=repo_path).stdout


def list_changed_files(repo_path: Path) -> list[str]:
    output = status_porcelain(repo_path)
    if not output:
        return []
    files: list[str] = []
    for line in output.splitlines():
        if len(line) >= 4:
            files.append(line[3:])
    return files


def list_conflict_files(repo_path: Path) -> list[str]:
    result = run_git(["diff", "--name-only", "--diff-filter=U"], cwd=repo_path)
    if not result.stdout:
        return []
    return result.stdout.splitlines()


def add_files(repo_path: Path, files: list[str]) -> None:
    if files:
        run_git(["add", *files], cwd=repo_path)


def add_all_changes(repo_path: Path) -> None:
    run_git(["add", "-u"], cwd=repo_path)


def diff_file(repo_path: Path, file_path: str) -> str:
    return run_git(["diff", "--", file_path], cwd=repo_path, check=False).stdout


def diff_stat_range(repo_path: Path, base_ref: str, head_ref: str = "HEAD") -> str:
    return run_git(
        ["diff", "--stat", f"{base_ref}...{head_ref}"],
        cwd=repo_path,
        check=False,
    ).stdout


def get_merge_base(repo_path: Path, target: str) -> str | None:
    result = run_git(["merge-base", "HEAD", target], cwd=repo_path, check=False)
    return result.stdout.strip() if result.returncode == 0 and result.stdout else None


def get_file_at_commit(repo_path: Path, commit_sha: str, file_path: str) -> str | None:
    result = run_git(["show", f"{commit_sha}:{file_path}"], cwd=repo_path, check=False)
    return result.stdout if result.returncode == 0 else None


def get_commits_for_file(
    repo_path: Path,
    since: str,
    until: str,
    file_path: str,
    max_count: int = 5,
) -> list[str]:
    result = run_git(
        ["log", "--oneline", f"-{max_count}", f"{since}..{until}", "--", file_path],
        cwd=repo_path,
        check=False,
    )
    return result.stdout.strip().splitlines() if result.stdout.strip() else []


def last_commit_for_file(repo_path: Path, file_path: str) -> str:
    result = run_git(
        ["log", "-1", "--pretty=%h %s", "--", file_path],
        cwd=repo_path,
        check=False,
    )
    return result.stdout.strip()
