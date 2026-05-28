# Architecture

## Module map

- `cli.py`: entry point and workflow orchestration.
- `git_ops.py`: all Git subprocess calls.
- `conflict_parser.py`: parses `<<<<<<< / ======= / >>>>>>>` markers into segments.
- `conflict_classifier.py`: classifies conflicts as `IMPORTS`, `FORMATTING`, `LOCKFILE`, `DOCUMENTATION`, or `SEMANTIC`.
- `conflict_resolver.py`: applies rules, validates syntax, and stages files.
- `rules.py`: `resolve_imports`, `resolve_formatting`, `resolve_docs`, and `resolve_duplicate`.
- `lockfile_tools.py`: strips markers, detects the Yarn driver, and regenerates lockfiles.
- `inline_editor.py`: prompt_toolkit inline edit loop.
- `prompts.py`: terminal prompts for decisions.
- `state_manager.py`: persists rebase state between runs.
- `config.py`: `GrebaseConfig` dataclass.

## Data flow

1. `cli.py` validates the repository and resolves the target branch.
2. `git_ops.py` starts the rebase or resumes an active one.
3. `conflict_detector.py` finds conflicted files.
4. `conflict_parser.py` splits each file into text and conflict segments.
5. `conflict_classifier.py` decides whether a file or segment is safe.
6. `conflict_resolver.py` applies deterministic rules or defers to the user.
7. `git_ops.py` stages the result and continues the rebase.

## Adding a new conflict resolver

1. Add a resolver function in `grebase/rules.py`.
2. Add a `ConflictType` or segment classifier branch in `grebase/conflict_classifier.py`.
3. Update `grebase/conflict_resolver.py` to dispatch the new rule.
4. Add fixtures in `tests/fixtures/`.
5. Add coverage in `tests/test_classifier.py` and `tests/test_resolver.py`.

## Orientation note

During a git rebase:

- `<<<<<<< HEAD` is the target branch side.
- `>>>>>>>` is your feature commit side.

That is intentionally reversed inside `conflict_parser.py` so `segment.current`
means yours and `segment.incoming` means theirs for the rest of the codebase.
