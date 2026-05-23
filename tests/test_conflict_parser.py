from grebase.conflict_parser import (
    ConflictSegment,
    TextSegment,
    has_conflicts,
    parse_conflict_segments,
)


def test_has_conflicts_detects_markers() -> None:
    text = """before
<<<<<<< HEAD
one
=======
two
>>>>>>> origin/main
after
"""
    assert has_conflicts(text) is True


def test_has_conflicts_handles_crlf() -> None:
    text = "before\r\n<<<<<<< HEAD\r\none\r\n=======\r\ntwo\r\n>>>>>>> origin/main\r\nafter\r\n"
    assert has_conflicts(text) is True


def test_parse_conflict_segments_splits_text() -> None:
    text = """alpha
<<<<<<< HEAD
one
=======
two
>>>>>>> origin/main
omega
"""
    segments = parse_conflict_segments(text)
    assert isinstance(segments[0], TextSegment)
    assert isinstance(segments[1], ConflictSegment)
    assert isinstance(segments[2], TextSegment)
    conflict = segments[1]
    assert isinstance(conflict, ConflictSegment)
    assert conflict.current == "two\n"
    assert conflict.incoming == "one\n"
