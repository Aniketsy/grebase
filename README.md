# grebase

Safe, rule-based Git rebase assistant for terminal-first workflows.

## Overview
Grebase automates the safe parts of a rebase and prompts only when a decision
requires human judgment. It fetches the latest remote state, detects targets,
monitors conflicts, and applies deterministic resolutions when possible.

## Installation

```bash
pipx install grebase
```

For development:

```bash
pip install -e .[dev]
```

## Usage

```bash
grebase
grebase main
grebase origin/main
grebase run main
```

### Commands and Options
- `run` explicit subcommand (grebase defaults to this)
- `--continue` resume an in-progress rebase
- `--abort` abort the rebase
- `--skip` skip the current commit
- `--status` show porcelain status
- `--dry-run` simulate without writing files
- `--interactive/--non-interactive` prompt for unresolved conflicts (default: on)
- `--safe-only` only apply safe auto-resolutions
- `--policy` default policy for ambiguous conflicts: prompt, current, incoming
- `--verbose` verbose logging

## Supported Conflict Types
- Import conflicts (merge unique import lines)
- Formatting-only conflicts (whitespace-only changes)
- Documentation conflicts (safe merge for docs)
- Duplicate insert conflicts (deduplicate blocks)
- Lockfile conflicts (auto-regenerated when tool is available)

## Lockfile Regeneration
When a lockfile conflict is detected, grebase attempts to run the matching tool:
- `poetry.lock` -> `poetry lock`
- `Pipfile.lock` -> `pipenv lock`
- `package-lock.json` -> `npm ci`
- `yarn.lock` -> `yarn install`
- `pnpm-lock.yaml` -> `pnpm install`

If the tool is missing or fails, grebase prompts for manual resolution.

## Incoming Changes Summary
Grebase prints a diff summary between the target branch and your current branch
before rebasing to help you review incoming changes.

## Safety Philosophy
- Never overwrite semantic logic without a prompt
- Preserve Git workflow compatibility
- Log decisions clearly
- Always allow abort and manual resolution

## Contributing
See [docs/contributing.md](docs/contributing.md) for setup, standards, and tests.

## License
MIT. See [LICENSE](LICENSE).