"""Integration tests — full FastAPI app."""

from httpx import ASGITransport, AsyncClient
from src.api import create_app


async def test_health_returns_observability_ids() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "request_id" in body
    assert "correlation_id" in body
    assert "trace_id" in body
    assert response.headers.get("X-Request-ID")
    assert response.headers.get("X-Correlation-ID")
    assert response.headers.get("X-Trace-ID")
