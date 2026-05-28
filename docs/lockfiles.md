# Lockfiles

grebase handles lockfiles as a special case because they are usually machine-generated.

## Supported lockfiles

| File | Command |
|---|---|
| `poetry.lock` | `poetry lock --no-update` |
| `Pipfile.lock` | `pipenv lock` |
| `package-lock.json` | `npm install` |
| `yarn.lock` | `yarn install` |
| `pnpm-lock.yaml` | `pnpm install` |

## Safety rules

- Conflict markers are stripped before the regeneration command runs.
- The regeneration command is chosen from the lockfile name.
- If the tool is missing or fails, grebase falls back to manual resolution.
- `yarn.lock` is skipped when a Yarn merge driver is already configured.
- Interactive mode asks for confirmation before touching a lockfile.
- `--safe-only` skips lockfile regeneration entirely.

## Recommended workflow

1. Let grebase regenerate the lockfile when the change is clearly mechanical.
2. Review the diff with `git diff -- <lockfile>`.
3. If the lockfile changed unexpectedly, abort or resolve it manually.

## Why this exists

Most lockfile conflicts are churn, not logic.

This page keeps the command mapping and safety notes in one place so the README can stay short.
