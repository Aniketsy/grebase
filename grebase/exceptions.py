class GrebaseError(Exception):
    """Base error for grebase."""


class GitError(GrebaseError):
    """Git command failed or repository state is invalid."""


class ConflictError(GrebaseError):
    """Conflict parsing or resolution failed."""
