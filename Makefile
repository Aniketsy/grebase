PYTHON := python

.PHONY: test lint format typecheck

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m black .

typecheck:
	$(PYTHON) -m mypy grebase
