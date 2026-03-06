"""Per-command context for star ledger attribution."""

from contextvars import ContextVar, Token

_source: ContextVar[str] = ContextVar("star_ledger_source", default="unknown")
_reason: ContextVar[str] = ContextVar("star_ledger_reason", default="unknown")


def set_context(source: str | None, reason: str | None) -> tuple[Token, Token]:
    """Set command context for the current async task."""
    return (
        _source.set(source or "unknown"),
        _reason.set(reason or "unknown"),
    )


def reset_context(tokens: tuple[Token, Token]) -> None:
    """Reset command context for the current async task."""
    source_token, reason_token = tokens
    _source.reset(source_token)
    _reason.reset(reason_token)


def get_context() -> tuple[str, str]:
    """Get current command context (source, reason)."""
    return _source.get(), _reason.get()
