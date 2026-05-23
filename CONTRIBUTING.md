# Contributing

Thanks for helping improve grebase. This guide focuses on quick setup and a clear path for first contributions.

## Setup

```bash
git clone https://github.com/Aniketsy/grebase
cd grebase
python -m pip install -e .[dev]
```

Requirements:
- Python 3.11+
- Git

## Run tests

```bash
python -m pytest
```

## Add a new conflict resolver

1. Add a rule function in `grebase/rules.py`.
2. Add a `ConflictType` value in `grebase/conflict_classifier.py`.
3. Wire the rule into `grebase/conflict_resolver.py`.
4. Add a fixture in `tests/fixtures/`.
5. Add tests in `tests/test_classifier.py` and `tests/test_resolver.py`.

## Linting

```bash
python -m ruff check grebase tests
python -m black grebase tests
python -m mypy grebase
```

## PR checklist

- Tests added or updated for new behavior.
- `ruff`, `black`, and `mypy` are clean.
- Docs updated for user-facing changes.
- PR is focused and easy to review.
