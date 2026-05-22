from pathlib import Path

from grebase.conflict_classifier import ConflictType, classify_conflict
from grebase.conflict_parser import parse_conflict_segments

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
	return (FIXTURES / name).read_text(encoding="utf-8")


def test_classifies_import_conflict() -> None:
	text = _load("import_conflict.py")
	segments = parse_conflict_segments(text)
	assert classify_conflict("sample.py", segments) == ConflictType.IMPORTS


def test_classifies_formatting_conflict() -> None:
	text = _load("formatting_conflict.txt")
	segments = parse_conflict_segments(text)
	assert classify_conflict("sample.py", segments) == ConflictType.FORMATTING


def test_classifies_docs_conflict() -> None:
	text = _load("docs_conflict.md")
	segments = parse_conflict_segments(text)
	assert classify_conflict("README.md", segments) == ConflictType.DOCUMENTATION


def test_classifies_duplicate_conflict() -> None:
	text = _load("duplicate_conflict.py")
	segments = parse_conflict_segments(text)
	assert classify_conflict("sample.py", segments) == ConflictType.DUPLICATE


def test_classifies_semantic_conflict() -> None:
	text = _load("semantic_conflict.py")
	segments = parse_conflict_segments(text)
	assert classify_conflict("sample.py", segments) == ConflictType.SEMANTIC


def test_classifies_lockfile_conflict() -> None:
	text = _load("poetry.lock")
	segments = parse_conflict_segments(text)
	assert classify_conflict("poetry.lock", segments) == ConflictType.LOCKFILE
