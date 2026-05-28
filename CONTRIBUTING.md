# Contributing

Thanks for helping improve grebase. This guide is the quick start for setting up the repo, running checks, and adding new conflict rules.

## Setup

```bash
git clone https://github.com/Aniketsy/grebase
cd grebase
python -m pip install -e .[dev]
```

Requirements:
- Python 3.11+

## Run tests

```bash
pytest -v #to run all tests
pytest tests/test_rules.py
pytest --cov=grebase
```

## Linting

```bash
ruff check grebase tests
black grebase tests
mypy grebase
```

## Add a conflict resolver

1. Add a rule in `grebase/rules.py`.
2. Add a `ConflictType` in `grebase/conflict_classifier.py`.
3. Update the classifier logic in `_is_X_block()` or `classify_segment()`.
4. Wire the rule into `grebase/conflict_resolver.py`.
5. Add a fixture in `tests/fixtures/`.
6. Add tests in `tests/test_classifier.py` and `tests/test_resolver.py`.

## PR checklist

- `pytest` passes.
- New behavior has tests.
- Existing tests still pass.
- `ruff`, `black`, and `mypy` are clean.
- Changes are small and focused.
