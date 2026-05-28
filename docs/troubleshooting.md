# Troubleshooting

## Dirty working tree

grebase expects a clean tracked tree before it starts.

If you see a dirty-tree error, commit or stash the tracked changes and run grebase again.

## Rebase already in progress

Use one of these commands:

```bash
grebase --continue
grebase --skip
grebase --abort
```

If none of those apply, inspect `.git/rebase-merge` or `.git/rebase-apply` to confirm the rebase state.

## Lockfile tool missing

Install the relevant package manager, then rerun the command.

Examples:

- `poetry`
- `pipenv`
- `npm`
- `yarn`
- `pnpm`

## Syntax error after auto-resolution

grebase validates Python files after it writes them.

If the file is restored and the rebase stops, the conflict was not safe to auto-resolve. Resolve it manually and continue.

## Target branch detection fails

Pass the branch explicitly:

```bash
grebase main
grebase origin/main
```

## Need more detail

- Use `--verbose` to see more workflow output.
- Use `--dry-run` to preview the decisions before writing files.
- Check `.git/grebase.log` if you enabled `--audit`.