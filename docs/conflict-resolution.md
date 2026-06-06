# Conflict resolution
 
This page explains exactly how grebase decides what to fix automatically and what to ask you about. Understanding this helps you trust what grebase does — and know when to step in.
 
---
 
## The core idea
 
When Git finds a conflict, it marks the file like this:
 
```
<<<<<<< HEAD
import { login, logout } from './auth'
=======
import { login } from './auth'
>>>>>>> feature/auth
```
 
The top section is the incoming branch's version. The bottom is yours.
 
Most conflicts like this one are **boring** — two developers changed the import list in different ways. grebase detects this and merges them silently, without asking you. Only changes that affect real logic get escalated.
 
---
 
## Conflict type overview
 
grebase classifies every conflict before deciding what to do:
 
| Type | What it means | grebase action |
|---|---|---|
| `IMPORTS` | Only import / require statements changed | Auto-resolved |
| `FORMATTING` | Only whitespace, spacing, or indentation changed | Auto-resolved |
| `DUPLICATE` | Identical code was added on both sides | Auto-resolved |
| `DOCUMENTATION` | Only `.md`, `.rst`, or `.txt` content changed | Auto-resolved |
| `LOCKFILE` | A package lockfile (e.g. `yarn.lock`) changed | Regenerated automatically |
| `SEMANTIC` | Actual logic, values, or behaviour changed | You decide |
 
Lockfiles and documentation files are classified at the **whole-file level** — grebase handles the entire file in one step. Everything else is resolved **segment by segment**, so a file can have a mix of safe and semantic conflicts. One tricky block does not hold up the easy ones.
 
---
 
## What gets auto-resolved
 
### Import conflicts
 
grebase merges import statements from both sides into a single clean block.
 
Rules applied:
 
- Unique imports from both sides are combined
- Duplicate imports are removed (kept only once)
- `from ... import (...)` multi-line blocks are collapsed before merging
- `from __future__ import ...` lines are always kept at the top
- If one side uses a `*` wildcard import, it takes precedence over specific names
- If a developer intentionally removed an import on the base branch, that removal is respected
**Example — before (conflicted):**
 
```python
<<<<<<< HEAD
import os
import sys
import json
=======
import os
import re
>>>>>>> feature/parsing
```
 
**After grebase auto-resolves:**
 
```python
import json
import os
import re
import sys
```
 
> JavaScript and TypeScript `import` statements are handled separately from Python imports — they follow their own merge rules.
 
---
 
### Formatting conflicts
 
grebase accepts the non-whitespace version silently. This covers:
 
- Trailing whitespace differences
- Operator spacing (`x=1` vs `x = 1`)
- Indentation differences
**Exception:** indentation changes that structurally alter the code — for example, a block being moved inside or outside an `if` statement — are treated as semantic and escalated to you. grebase does not guess at structural changes.
 
---
 
### Duplicate conflicts
 
When the same lines were added independently on both sides, grebase keeps one copy and drops the other.
 
**Before:**
 
```
<<<<<<< HEAD
console.log('Initialising app')
=======
console.log('Initialising app')
>>>>>>> feature/logging
```
 
**After:** `console.log('Initialising app')` — just once.
 
---
 
### Documentation conflicts
 
For files that are purely documentation (`.md`, `.rst`, plain `.txt`), grebase merges changes line by line. Duplicate lines are de-duplicated while preserving order. The merged result keeps everything from both sides, minus the repeated lines.
 
---
 
### Lockfile conflicts
 
Lockfiles like `yarn.lock` or `poetry.lock` are auto-generated — editing them manually almost always causes broken installs. grebase detects which package manager owns the file and re-runs it from scratch:
 
| Lockfile | Command grebase runs |
|---|---|
| `yarn.lock` | `yarn install` |
| `package-lock.json` | `npm ci` |
| `pnpm-lock.yaml` | `pnpm install` |
| `poetry.lock` | `poetry lock` |
| `Pipfile.lock` | `pipenv lock` |
 
If the required tool is not installed or the command fails, grebase falls back to prompting you rather than silently producing a broken lockfile.
 
See [lockfiles.md](lockfiles.md) for the full details, including Yarn merge driver detection.
 
---
 
## What never gets auto-resolved
 
A **semantic conflict** is anything that could change the behaviour of your code. grebase will never silently resolve these — it always asks you.
 
Examples of semantic conflicts:
 
- Changing a function's body or return value
- Adding or removing a branch in `if / else` logic
- Changing a constant, config value, or environment variable
- Any file where at least one conflict block contains real logic, even if other blocks are safe
When grebase detects a semantic conflict, it pauses and shows you a decision menu:
 
```
!  Conflict: src/utils.ts — semantic change detected
 
   1. Keep mine        2. Take theirs
   3. Keep mine (all)  4. Take theirs (all)
   5. Show diff        6. Open editor    7. Abort
   > _
```
 
Choose **5 (Show diff)** if you are unsure — it shows you exactly what changed on each side before you commit to a decision.
 
---
 
## Safety guarantees
 
grebase is designed to fail safe:
 
- **Python files are syntax-checked** after every auto-resolution. If the result would be invalid Python, grebase restores the original file and escalates to you.
- **Semantic conflicts are never touched automatically.** Any ambiguity is treated as semantic.
- **Lockfiles are only regenerated** using the correct package manager command — never hand-edited.
- **Yarn merge driver detection** — if the repo has its own Yarn merge driver configured, grebase respects it and does not override the repo's own rules.
- **Everything is abortable.** Run `grebase --abort` at any point to restore your branch exactly as it was before the rebase started.
---
 
## Flags that affect conflict resolution
 
| Flag | What it does |
|---|---|
| `--safe-only` | Auto-resolve only the most conservative cases; skip lockfile regeneration; prompt for everything else |
| `--policy mine` | Your branch wins by default when grebase is uncertain |
| `--policy theirs` | The target branch wins by default when grebase is uncertain |
| `--audit` | Write a log of every resolution decision to `.git/grebase.log` |
| `--dry-run` | Preview what would be resolved without writing any files |
 
---
 
## See also
 
- [Lockfiles](lockfiles.md) — detailed lockfile handling and the Yarn merge driver
- [Flags reference](flags.md) — full flag documentation
- [Architecture](architecture.md) — how the classifier and resolvers are structured in code
