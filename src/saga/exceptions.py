"""Saga domain errors mapped to HTTP responses in the API layer."""


class SagaError(Exception):
    """Base saga error with optional client-facing detail."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        self.detail = detail or message
        super().__init__(message)


class SessionNotFoundError(SagaError):
    """Checkout session does not exist."""


class ProductNotFoundError(SagaError):
    """Catalog SKU not found for hold/confirm."""


class InvalidStateTransitionError(SagaError):
    """Session state does not allow the requested operation."""


class HoldExpiredError(SagaError):
    """Hold TTL elapsed before confirm."""


class InsufficientStockError(SagaError):
    """Requested quantity exceeds available IHMS inventory."""


class IdempotencyConflictError(SagaError):
    """Idempotency key reused with a different request payload."""


class CompensationIncompleteError(SagaError):
    """Hold release failed after order failure — session not marked compensated."""


class OrderStatusUnknownError(CompensationIncompleteError):
    """Order creation may have succeeded, but reconciliation could not verify it."""
