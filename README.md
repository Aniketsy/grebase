# grebase

Rebase without the wreckage.
Handles the obvious. Asks you about the rest.

[![CI](https://github.com/Aniketsy/grebase/actions/workflows/ci.yml/badge.svg)](https://github.com/Aniketsy/grebase/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/grebase?color=0A7AFF&label=pypi)](https://pypi.org/project/grebase)
[![License: MIT](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)
![Status: Active](https://img.shields.io/badge/status-active%20development-orange)

```
$ grebase main

✓ Repository detected
✓ Current branch: feature
✓ Target branch: main
i Incoming changes summary:
  M auth.py
! Conflict: auth.py
i Last change: a3f1c2e feat: improve token hashing
i Choose how to resolve. If unsure, use Show diff.
Select resolution:
1. Keep mine (this file)
2. Keep theirs (this file)
3. Keep mine (all remaining)
4. Keep theirs (all remaining)
5. Show diff
6. Skip
7. Abort
> 2
```

</div>

---

## Why grebase?

Rebasing is painful because of the **middle part** — editing conflict markers in files, remembering to `git add` instead of `git commit`, repeating this for every commit. Most conflicts are actually trivial (import reordering, lockfile churn, whitespace) but git treats them all the same.

grebase handles the boring ones automatically and surfaces only the ones that genuinely need your eyes.

---

## Install

```bash
pipx install grebase
```

> Requires Python 3.11+. `pipx` is recommended so it doesn't pollute your global environment.

**For contributors:**
```bash
git clone https://github.com/Aniketsy/grebase
pip install -e .[dev]
```

**Windows notes:**
- Install Git for Windows and make sure `git` is on your PATH.
- Install pipx and run `pipx ensurepath` before installing grebase.

---

## Usage

```bash
grebase              # auto-detect target branch and rebase
grebase main         # rebase onto main
grebase origin/main  # rebase onto a specific remote ref
```

**Mid-rebase commands** (when a rebase is already in progress):
```bash
grebase --continue   # after manually resolving a conflict
grebase --skip       # skip the current commit
grebase --abort      # bail out and restore original state
```

**Common flags:**

| Flag | Description |
|---|---|
| `--remote <name>` | Remote to use: `auto`, `origin`, `upstream`, or any name |
| `--policy <mode>` | Default for ambiguous conflicts: `prompt` · `mine` (yours) · `theirs` (target). Aliases: `current`, `incoming` |
| `--safe-only` | Auto-resolve only, never guess — prompt for everything else |
| `--non-interactive` | No prompts — exits if a decision is needed |
| `--dry-run` | Simulate the full rebase without writing any files |
| `--audit` | Write a decision log to `.git/grebase.log` |
| `--status` | Show current rebase state |
| `--verbose` | Detailed output |
| `--version` | Show grebase version and exit |

---

## What it auto-resolves

grebase applies deterministic rules. It never guesses at logic — if a conflict looks semantic, it asks you.

| Conflict type | What grebase does |
|---|---|
| **Import statements** | Merges unique imports from both sides |
| **Whitespace / formatting** | Takes the non-whitespace version silently |
| **Documentation** | Safely merges when both sides only change docs |
| **Duplicate inserts** | Deduplicates identical blocks |
| **Lockfiles** | Regenerates using the right package manager |

**Lockfile regeneration** — grebase runs the correct tool automatically:

```
poetry.lock       → poetry lock
Pipfile.lock      → pipenv lock
package-lock.json → npm ci
yarn.lock         → yarn install
pnpm-lock.yaml    → pnpm install
```

If the tool isn't installed or fails, grebase falls back to prompting you.

---

## Safety

- **Never rewrites logic silently.** Semantic conflicts always get a prompt.
- **Always abortable.** Hit `Ctrl+C` or run `grebase --abort` to restore your branch exactly as it was.
- **Audit trail.** `--audit` logs every decision grebase makes to `.git/grebase.log`.
- **Dry-run first.** Not sure? `grebase --dry-run` shows exactly what would happen.

---

## Troubleshooting

**Dirty working tree**
Commit or stash your changes first, then run grebase.

**Rebase already in progress**
Use `grebase --continue`, `grebase --abort`, or `grebase --skip`.

**Lockfile tool missing**
Install the relevant package manager, or resolve the lockfile manually and run `grebase --continue`.

---

## Contributing

Contributions are very welcome — this is early-stage and your feedback matters.

- Read [CONTRIBUTING.md](CONTRIBUTING.md) to get started
- Keep PRs small and focused
- Add tests for any new behavior
- New conflict resolution rules go in `grebase/rules.py` and `grebase/conflict_classifier.py`

```bash
# run tests
pytest

# run against a local repo
grebase --dry-run --verbose
```

---

MIT License · Built for devs who live in the terminal


