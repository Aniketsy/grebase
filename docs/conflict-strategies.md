# Conflict Strategies

## Imports
Merge unique import lines while preserving order.

## Formatting only
If normalized content matches, keep incoming formatting.

## Documentation
Merge both sides and de-duplicate identical lines.

## Duplicates
If both sides are identical, keep one copy.

## Lockfiles
Grebase attempts to regenerate lockfiles using the corresponding package manager
when available (poetry, pipenv, npm, yarn, pnpm). If the tool is missing or the
command fails, it falls back to manual resolution.
