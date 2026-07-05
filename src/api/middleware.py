"""Request, correlation, and trace ID middleware."""

import logging
import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.observability.constants import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    TRACE_ID_HEADER,
)
from src.observability.context import bind_log_context, clear_log_context, reset_log_context

HTTP_LOGGER = logging.getLogger("checkout.http")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Inject and propagate observability identifiers on every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        trace_id = request.headers.get(TRACE_ID_HEADER) or str(uuid.uuid4())
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or request_id

        request.state.request_id = request_id
        request.state.trace_id = trace_id
        request.state.correlation_id = correlation_id

        token = bind_log_context(
            request_id=request_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            HTTP_LOGGER.exception(
                "request failed",
                extra={
                    "step": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(elapsed_ms, 2),
                },
            )
            raise
        else:
            elapsed_ms = (time.perf_counter() - started) * 1000
            HTTP_LOGGER.info(
                "request completed",
                extra={
                    "step": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(elapsed_ms, 2),
                },
            )
            response.headers[REQUEST_ID_HEADER] = request_id
            response.headers[TRACE_ID_HEADER] = trace_id
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            return response
        finally:
            reset_log_context(token)
            clear_log_context()
