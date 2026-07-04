"""EC-OPS HTTP client — sole caller of EC-OPS order API."""

import httpx

from src.gateway.ecops_models import OrderCreate, OrderResponse, OrderStatus
from src.gateway.headers import ObservabilityHeaders
from src.gateway.http_utils import map_transport_error, raise_for_ecops_response


class EcOpsClient:
    """Async client for EC-OPS order endpoints."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        bearer_token: str,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._bearer_token = bearer_token

    def _auth_headers(self, headers: ObservabilityHeaders) -> dict[str, str]:
        merged = headers.as_dict()
        if self._bearer_token:
            merged["Authorization"] = f"Bearer {self._bearer_token}"
        return merged

    async def create_order(
        self,
        payload: OrderCreate,
        headers: ObservabilityHeaders,
        *,
        idempotency_key: str | None = None,
    ) -> OrderResponse:
        extra: dict[str, str] = {}
        if idempotency_key:
            extra["Idempotency-Key"] = idempotency_key
        try:
            response = await self._client.post(
                f"{self._base_url}/orders",
                json=payload.model_dump(mode="json"),
                headers={**self._auth_headers(headers), **extra},
            )
        except httpx.HTTPError as exc:
            raise map_transport_error(exc) from exc
        raise_for_ecops_response(response)
        return OrderResponse.model_validate(response.json())

    async def get_order(self, order_id: str, headers: ObservabilityHeaders) -> OrderResponse:
        try:
            response = await self._client.get(
                f"{self._base_url}/orders/{order_id}",
                headers=self._auth_headers(headers),
            )
        except httpx.HTTPError as exc:
            raise map_transport_error(exc) from exc
        raise_for_ecops_response(response)
        return OrderResponse.model_validate(response.json())

    async def list_orders(
        self,
        headers: ObservabilityHeaders,
        *,
        status: OrderStatus | None = None,
    ) -> list[OrderResponse]:
        params: dict[str, str] = {}
        if status is not None:
            params["status"] = status.value
        try:
            response = await self._client.get(
                f"{self._base_url}/orders",
                params=params or None,
                headers=self._auth_headers(headers),
            )
        except httpx.HTTPError as exc:
            raise map_transport_error(exc) from exc
        raise_for_ecops_response(response)
        return [OrderResponse.model_validate(item) for item in response.json()]

    async def find_order_by_client_reference(
        self,
        client_reference: str,
        headers: ObservabilityHeaders,
    ) -> OrderResponse | None:
        orders = await self.list_orders(headers)
        return next((order for order in orders if order.client_reference == client_reference), None)
