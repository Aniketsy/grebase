<div align="center">

# grebase

Rebase without the wreckage.
Handles the obvious. Asks you about the rest.

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/grebase?color=0A7AFF&label=pypi)](https://pypi.org/project/grebase)
[![License: MIT](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)
![Status: Active](https://img.shields.io/badge/status-active%20development-orange)

```
$ grebase main

  ✔  fetched origin
  ✔  3 commits ahead, 7 commits behind
  ⚡  conflict in api/auth.js — import order only → auto-resolved
  ⚡  conflict in yarn.lock → regenerating with yarn install
  ?  conflict in src/utils.ts — semantic change detected

  [1] keep yours   [2] take theirs   [3] show diff   [4] open editor
  → 2

  ✔  rebase complete — 7 commits applied cleanly
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

> Requires Python 3.9+. `pipx` is recommended so it doesn't pollute your global environment.

**For contributors:**
```bash
git clone https://github.com/your-org/grebase
pip install -e .[dev]
```

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
| `--policy <mode>` | Default for ambiguous conflicts: `prompt` · `current` · `incoming` |
| `--safe-only` | Auto-resolve only, never guess — prompt for everything else |
| `--non-interactive` | No prompts — exits if a decision is needed |
| `--dry-run` | Simulate the full rebase without writing any files |
| `--audit` | Write a decision log to `.git/grebase.log` |
| `--status` | Show current rebase state |
| `--verbose` | Detailed output |

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

## Before it starts

grebase prints a summary of incoming changes before touching anything — so you know what's about to happen:

```
  main is 7 commits ahead of your branch
  ─────────────────────────────────────────
  a3f1c2e  fix: update token expiry logic
  8bc09d1  feat: add rate limiting middleware
  ...
  → 2 files will likely conflict (api/auth.js, src/config.ts)
```

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

- Read [docs/contributing.md](docs/contributing.md) to get started
- Keep PRs small and focused
- Add tests for any new behavior
- New conflict resolution rules go in `grebase/resolvers/` — each rule is one file

```bash
# run tests
pytest

# run against a local repo
grebase --dry-run --verbose
```

---

<div align="center">

MIT License · Built for devs who live in the terminal

</div>
