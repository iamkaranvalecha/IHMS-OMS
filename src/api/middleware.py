"""Request, correlation, and trace ID middleware."""

import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"
TRACE_ID_HEADER = "X-Trace-ID"


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Inject and propagate observability identifiers on every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        trace_id = request.headers.get(TRACE_ID_HEADER) or str(uuid.uuid4())
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or request_id

        request.state.request_id = request_id
        request.state.trace_id = trace_id
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[TRACE_ID_HEADER] = trace_id
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
