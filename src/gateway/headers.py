"""Observability headers for upstream gateway calls."""

from dataclasses import dataclass

from src.observability.constants import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    TRACE_ID_HEADER,
)


@dataclass(frozen=True, slots=True)
class ObservabilityHeaders:
    """Outbound header bundle for gateway HTTP calls."""

    request_id: str
    correlation_id: str
    trace_id: str

    def as_dict(self) -> dict[str, str]:
        return {
            REQUEST_ID_HEADER: self.request_id,
            CORRELATION_ID_HEADER: self.correlation_id,
            TRACE_ID_HEADER: self.trace_id,
        }
