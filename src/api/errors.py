"""Map saga and gateway exceptions to HTTP responses."""

from fastapi import HTTPException

from src.gateway.exceptions import (
    GatewayError,
    GatewayTimeoutError,
    HoldConflictError,
    HoldNotFoundError,
    HoldValidationError,
    UpstreamError,
)
from src.saga.exceptions import (
    CompensationIncompleteError,
    HoldExpiredError,
    InvalidStateTransitionError,
    ProductNotFoundError,
    SagaError,
    SessionNotFoundError,
)


def http_exception_for_error(exc: Exception) -> HTTPException:
    """Translate domain errors into ProblemDetails-style HTTP responses."""
    if isinstance(exc, SessionNotFoundError):
        return HTTPException(status_code=404, detail=exc.detail)
    if isinstance(exc, ProductNotFoundError):
        return HTTPException(status_code=404, detail=exc.detail)
    if isinstance(exc, HoldExpiredError):
        return HTTPException(status_code=409, detail=exc.detail)
    if isinstance(exc, InvalidStateTransitionError):
        return HTTPException(status_code=409, detail=exc.detail)
    if isinstance(exc, HoldNotFoundError):
        return HTTPException(status_code=404, detail=exc.problem.detail or str(exc))
    if isinstance(exc, HoldConflictError):
        return HTTPException(status_code=409, detail=exc.problem.detail or str(exc))
    if isinstance(exc, HoldValidationError):
        return HTTPException(status_code=422, detail=exc.problem.detail or str(exc))
    if isinstance(exc, CompensationIncompleteError):
        return HTTPException(status_code=503, detail=exc.detail)
    if isinstance(exc, GatewayTimeoutError):
        return HTTPException(status_code=504, detail="Upstream request timed out")
    if isinstance(exc, UpstreamError):
        return HTTPException(status_code=502, detail=exc.problem.detail or str(exc))
    if isinstance(exc, GatewayError):
        return HTTPException(status_code=502, detail=str(exc))
    if isinstance(exc, SagaError):
        return HTTPException(status_code=400, detail=exc.detail)
    if isinstance(exc, HTTPException):
        return exc
    return HTTPException(status_code=500, detail=str(exc))
