# Flags reference

| Flag | Description |
|---|---|
| `--policy mine|theirs` | Default for ambiguous conflicts. `mine` keeps your branch side, `theirs` keeps the target side. |
| `--safe-only` | Only auto-resolve conflicts that are deterministic and safe. Skip lockfile regeneration and semantic guesses. |
| `--dry-run` | Simulate the workflow without writing files or staging changes. |
| `--non-interactive` | Do not prompt. Exit with a non-zero status if a decision is needed. |
| `--audit` | Write decisions to `.git/grebase.log`. |
| `--remote <name>` | Choose which remote to use for target detection and fetches. |
| `--status` | Print the current working tree / rebase status and exit. |
| `--verbose` | Emit debug-level workflow details. |
| `--version` | Print the installed grebase version and exit. |

## `--policy`

Use `--policy mine` when your branch should win by default.

Use `--policy theirs` when the target branch should win by default.

Aliases:

- `current` maps to `mine`
- `incoming` maps to `theirs`

## `--safe-only`

`--safe-only` keeps grebase conservative.

It still resolves deterministic cases like imports, formatting, documentation, and duplicates.
It skips lockfile regeneration and anything that would require a guess.

## `--dry-run`

`--dry-run` walks the workflow and prints what would happen, but it does not write files.

That is useful for checking whether a repository is likely to need manual input.
