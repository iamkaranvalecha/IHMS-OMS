"""Shared upstream HTTP response handling."""

import httpx

from src.gateway.exceptions import (
    GatewayError,
    GatewayTimeoutError,
    HoldConflictError,
    HoldNotFoundError,
    HoldValidationError,
    OrderNotFoundError,
    OrderValidationError,
    UpstreamError,
    UpstreamProblem,
)


def _parse_problem(response: httpx.Response) -> UpstreamProblem:
    detail: str | None = None
    title: str | None = None
    content_type = response.headers.get("content-type", "")
    if "json" in content_type:
        try:
            body = response.json()
            detail = body.get("detail") or body.get("title")
            title = body.get("title")
        except ValueError:
            detail = response.text or None
    else:
        detail = response.text or None
    return UpstreamProblem(status_code=response.status_code, detail=detail, title=title)


def raise_for_ihms_response(response: httpx.Response) -> None:
    """Map IHMS HTTP status to typed gateway exceptions."""
    if response.is_success:
        return
    problem = _parse_problem(response)
    if response.status_code == 404:
        raise HoldNotFoundError(problem)
    if response.status_code == 409:
        raise HoldConflictError(problem)
    if response.status_code == 422:
        raise HoldValidationError(problem)
    raise UpstreamError(problem)


def raise_for_ecops_response(response: httpx.Response) -> None:
    """Map EC-OPS HTTP status to typed gateway exceptions."""
    if response.is_success:
        return
    problem = _parse_problem(response)
    if response.status_code == 404:
        raise OrderNotFoundError(problem)
    if response.status_code == 422:
        raise OrderValidationError(problem)
    raise UpstreamError(problem)


def map_transport_error(exc: httpx.HTTPError) -> GatewayError:
    if isinstance(exc, httpx.TimeoutException):
        return GatewayTimeoutError(str(exc))
    return GatewayError(str(exc))
