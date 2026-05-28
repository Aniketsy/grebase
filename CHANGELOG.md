# Changelog

## 0.2.0 - unreleased

### Fixed
- Use `npm install` instead of `npm ci` for package-lock regeneration.
- Use `poetry lock --no-update` instead of `poetry lock` to avoid silent upgrades.
- Strip conflict markers before regenerating lockfiles.
- Swap the `--policy current/incoming` labels back to the correct sides.
- Make option 5 re-prompt instead of exiting.
- Stop classifying JS / TS imports as Python imports.
- Keep `from __future__ import annotations` at the top.
- Prevent star imports from merging with specific names.
- Treat indentation changes as structural, not formatting-only.
- Parse multiline parenthesized imports correctly.

### Added
- Add the `--version` flag.
- Add `--policy mine/theirs` aliases.
- Add `resolve_with_both` for mine-first or theirs-first resolution.
- Add the inline terminal editor for manual conflict edits.
- Detect the Yarn merge driver via `.gitattributes`.
- Warn before regenerating lockfiles and ask for confirmation.
- Validate syntax after auto-resolution.
- Respect intentional deletions in import resolution.
- Add the Windows CI matrix.
- Reach 131 tests and 87% coverage.

## 0.1.0
- Initial public release with CLI scaffold and core workflows.
