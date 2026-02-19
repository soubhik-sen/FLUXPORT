from __future__ import annotations

from contextvars import ContextVar


_current_bearer_token: ContextVar[str | None] = ContextVar(
    "current_bearer_token",
    default=None,
)


def set_current_bearer_token(token: str | None) -> None:
    normalized = (token or "").strip()
    _current_bearer_token.set(normalized or None)


def get_current_bearer_token() -> str | None:
    token = _current_bearer_token.get()
    normalized = (token or "").strip()
    return normalized or None
