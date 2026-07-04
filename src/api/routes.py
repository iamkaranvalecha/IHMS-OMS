"""API route modules."""

from fastapi import APIRouter, Request

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
async def health(request: Request) -> dict[str, str]:
    """Liveness probe with observability IDs echoed for debugging."""
    return {
        "status": "ok",
        "request_id": request.state.request_id,
        "correlation_id": request.state.correlation_id,
        "trace_id": request.state.trace_id,
    }
