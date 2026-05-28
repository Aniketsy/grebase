# Conflict resolution

## How grebase classifies conflicts

grebase separates conflicts into deterministic and semantic cases.

- `IMPORTS` - import-only blocks that can be merged safely.
- `FORMATTING` - whitespace-only differences.
- `DUPLICATE` - identical blocks inserted on both sides.
- `DOCUMENTATION` - doc-only changes in Markdown / reStructuredText / text files.
- `LOCKFILE` - package lockfiles that can be regenerated.
- `SEMANTIC` - anything that changes logic, values, or meaning.

File-level classification is used for lockfiles and documentation files.
Other files can be resolved segment-by-segment so one safe block does not block another.

## What gets auto-resolved

### Import conflicts

- unique imports from both sides are merged
- repeated imports are deduplicated
- `from ... import (...)` blocks are collapsed before merging
- `from __future__ import ...` stays at the top
- `*` import wins over specific names
- intentional removals from the base branch are respected
- JS / TS import conflicts are not treated as Python imports

### Formatting conflicts

- whitespace-only differences are accepted
- operator spacing and trailing whitespace are normalized
- indentation changes that alter structure are not treated as formatting-only

### Duplicate conflicts

- identical blocks are kept once
- duplicate inserts are collapsed instead of being repeated

### Documentation conflicts

- documentation-only changes are merged line by line
- duplicates are de-duplicated while preserving order

## What never gets auto-resolved

Semantic changes are left for you.

Examples:

- changing a function body
- adding or removing a branch in control flow
- changing values in a config or settings file
- mixed blocks where at least one conflict block is semantic

## Safety guarantees

- Every Python or Pythonw auto-resolution is syntax-checked after writing.
- If the output would be invalid Python, grebase restores the original file.
- Lockfiles are only regenerated with the appropriate package manager command.
- Yarn merge driver detection prevents grebase from fighting repo-level merge rules.