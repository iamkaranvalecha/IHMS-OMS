"""Request-scoped observability context for structured logs."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, fields

_log_context: ContextVar[LogContext | None] = ContextVar("log_context", default=None)


@dataclass(frozen=True, slots=True)
class LogContext:
    """Fields merged into every structured log line in this request."""

    request_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    session_id: str | None = None
    hold_id: str | None = None
    order_id: str | None = None


def get_log_context() -> LogContext | None:
    return _log_context.get()


def bind_log_context(**kwargs: str | None) -> Token[LogContext | None]:
    current = _log_context.get() or LogContext()
    updates = {field.name: getattr(current, field.name) for field in fields(LogContext)}
    for key, value in kwargs.items():
        if key in updates and value is not None:
            updates[key] = value
    return _log_context.set(LogContext(**updates))


def reset_log_context(token: Token[LogContext | None]) -> None:
    _log_context.reset(token)


def clear_log_context() -> None:
    _log_context.set(None)
