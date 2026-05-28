<div align="center">
  <img src="assets/banner.svg" alt="grebase — git rebase without the fear" width="680"/>
  <br/><br/>

  [![CI](https://github.com/Aniketsy/grebase/actions/workflows/ci.yml/badge.svg)](https://github.com/Aniketsy/grebase/actions/workflows/ci.yml)
  [![PyPI](https://img.shields.io/pypi/v/grebase?color=0A7AFF&label=pypi)](https://pypi.org/project/grebase)
  [![License: MIT](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)
  [![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
  ![Status](https://img.shields.io/badge/status-active%20development-orange)

</div>

---

## Why grebase?

You run `git` rebase and suddenly you're jumping between files, manually resolving each conflict, running git add on everything - and somehow unrelated commits ends up in your PR. **grebase** handles the whole thing from your terminal so none of that happens.

```bash
pipx install grebase
grebase main
```

---

## What it auto-resolves

Most conflicts fall into a small set of deterministic cases.

See [docs/conflict-resolution.md](docs/conflict-resolution.md) and
[docs/lockfiles.md](docs/lockfiles.md) for the full rules and safety details.

---

## How it looks

```
$ grebase main

✓  Repository detected
✓  Current branch: feature/auth-improvements
✓  Target branch:  main
◆  Incoming changes — auth.py, yarn.lock
✓  import conflict in auth.py — auto-resolved
✓  yarn.lock — regenerated via yarn install
!  Conflict: utils.ts — semantic change detected

   1. Keep mine        2. Take theirs
   3. Keep mine (all)  4. Take theirs (all)
   5. Show diff        6. Skip    7. Abort
   > 2

✓  Rebase complete — 3 commits applied cleanly
```

---

## Documentation

| Page | What's in it |
|---|---|
| [Getting started](docs/getting-started.md) | Install, first run, basic usage |
| [Flags reference](docs/flags.md) | Every flag explained |
| [Conflict resolution](docs/conflict-resolution.md) | What grebase auto-resolves and how |
| [Lockfiles](docs/lockfiles.md) | Per-tool commands, safety, yarn merge driver |
| [Troubleshooting](docs/troubleshooting.md) | Common errors and fixes |
| [Contributing](CONTRIBUTING.md) | Setup, tests, adding resolvers |
| [Architecture](docs/architecture.md) | How the codebase is structured |
| [Roadmap](docs/roadmap.md) | What is planned |

---

<div align="center">

MIT License · Built for devs who live in the terminal

</div>
