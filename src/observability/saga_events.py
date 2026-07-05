"""Saga step logging and metrics helpers."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.observability.context import bind_log_context
from src.observability.logging import get_logger
from src.observability.metrics import get_metrics_registry

SAGA_LOGGER = get_logger("checkout.saga")


def log_saga_step(
    step: str,
    message: str,
    *,
    level: int = logging.INFO,
    session_id: UUID | str | None = None,
    hold_id: str | None = None,
    order_id: str | None = None,
    outcome: str | None = None,
    **extra: Any,
) -> None:
    """Emit a structured saga log line with standard fields."""
    if session_id is not None:
        bind_log_context(session_id=str(session_id))
    if hold_id is not None:
        bind_log_context(hold_id=hold_id)
    if order_id is not None:
        bind_log_context(order_id=order_id)

    payload: dict[str, Any] = {"step": step}
    if outcome is not None:
        payload["outcome"] = outcome
    payload.update(extra)
    SAGA_LOGGER.log(level, message, extra=payload)


def record_hold_placed() -> None:
    get_metrics_registry().increment("holds_placed_total")


def record_hold_failed() -> None:
    get_metrics_registry().increment("holds_failed_total")


def record_confirm_success(*, reconciled: bool) -> None:
    registry = get_metrics_registry()
    registry.increment("confirms_success_total")
    if reconciled:
        registry.increment("confirms_reconciled_total")


def record_compensation() -> None:
    get_metrics_registry().increment("compensations_total")


def record_abandon() -> None:
    get_metrics_registry().increment("abandons_total")


def record_order_status_unknown() -> None:
    get_metrics_registry().increment("order_status_unknown_total")
