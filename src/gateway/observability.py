"""Structured logging for outbound gateway calls."""

import logging
from typing import Any

from src.gateway.headers import ObservabilityHeaders

GATEWAY_LOGGER = logging.getLogger("checkout.gateway")


def log_gateway_call(
    *,
    system: str,
    operation: str,
    headers: ObservabilityHeaders,
    **extra: Any,
) -> None:
    """Emit a trace-correlated log line before each upstream HTTP call."""
    GATEWAY_LOGGER.info(
        "upstream %s %s",
        system,
        operation,
        extra={
            "step": "gateway_call",
            "upstream": system,
            "operation": operation,
            "request_id": headers.request_id,
            "correlation_id": headers.correlation_id,
            "trace_id": headers.trace_id,
            **extra,
        },
    )
