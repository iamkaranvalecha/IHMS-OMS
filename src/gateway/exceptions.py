"""Gateway and upstream error types."""

from dataclasses import dataclass


class GatewayError(Exception):
    """Unexpected upstream failure."""


class GatewayTimeoutError(GatewayError):
    """Upstream request timed out."""


@dataclass
class UpstreamProblem:
    """RFC 7807-style upstream error detail."""

    status_code: int
    detail: str | None = None
    title: str | None = None


class UpstreamError(GatewayError):
    """Mapped upstream HTTP error with status code."""

    def __init__(self, problem: UpstreamProblem) -> None:
        self.problem = problem
        super().__init__(f"Upstream {problem.status_code}: {problem.detail or problem.title}")


class HoldNotFoundError(UpstreamError):
    """IHMS hold or product not found (404)."""


class HoldConflictError(UpstreamError):
    """IHMS hold conflict — stock, expired, already released (409)."""


class HoldValidationError(UpstreamError):
    """IHMS validation failure (422)."""


class OrderNotFoundError(UpstreamError):
    """EC-OPS order not found (404)."""


class OrderValidationError(UpstreamError):
    """EC-OPS validation failure (422)."""
