# Getting started

## Install

```bash
pipx install grebase
pip install grebase
```

Python 3.11+ is required.

Windows setup:

- Install Git for Windows.
- Run `pipx ensurepath` after installing `pipx`.

## First run

```bash
cd your-repo
grebase main
grebase origin/main
grebase
```

`grebase main` rebases onto `main`.

`grebase origin/main` rebases onto a remote ref.

`grebase` auto-detects the target branch when possible.

## Mid-rebase commands

```bash
grebase --continue
grebase --skip
grebase --abort
```

- `--continue` resumes after you stage a manual fix.
- `--skip` drops the current commit.
- `--abort` restores the branch state from before the rebase.

## For contributors

```bash
git clone https://github.com/Aniketsy/grebase
cd grebase
pip install -e .[dev]
pytest
```