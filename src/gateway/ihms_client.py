"""KB-IHMS HTTP client — sole caller of IHMS hold API."""

import httpx

from src.gateway.headers import ObservabilityHeaders
from src.gateway.http_utils import map_transport_error, raise_for_ihms_response
from src.gateway.ihms_models import (
    CreateHoldItemRequest,
    CreateHoldRequest,
    HoldResponse,
    InventoryItemResponse,
    ProductCatalogItemResponse,
)
from src.gateway.observability import log_gateway_call


class IhmsClient:
    """Async client for KB-IHMS hold endpoints."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        *,
        fulfill_optional: bool = True,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._fulfill_optional = fulfill_optional

    async def create_hold(
        self,
        items: list[CreateHoldItemRequest],
        headers: ObservabilityHeaders,
    ) -> HoldResponse:
        log_gateway_call(system="ihms", operation="POST /api/holds", headers=headers)
        payload = CreateHoldRequest(items=items)
        try:
            response = await self._client.post(
                f"{self._base_url}/api/holds",
                json=payload.model_dump(by_alias=True),
                headers=headers.as_dict(),
            )
        except httpx.HTTPError as exc:
            raise map_transport_error(exc) from exc
        raise_for_ihms_response(response)
        return HoldResponse.model_validate(response.json())

    async def get_hold(self, hold_id: str, headers: ObservabilityHeaders) -> HoldResponse:
        try:
            response = await self._client.get(
                f"{self._base_url}/api/holds/{hold_id}",
                headers=headers.as_dict(),
            )
        except httpx.HTTPError as exc:
            raise map_transport_error(exc) from exc
        raise_for_ihms_response(response)
        return HoldResponse.model_validate(response.json())

    async def release_hold(self, hold_id: str, headers: ObservabilityHeaders) -> None:
        try:
            response = await self._client.delete(
                f"{self._base_url}/api/holds/{hold_id}",
                headers=headers.as_dict(),
            )
        except httpx.HTTPError as exc:
            raise map_transport_error(exc) from exc
        raise_for_ihms_response(response)

    async def get_products(
        self, headers: ObservabilityHeaders
    ) -> list[ProductCatalogItemResponse]:
        log_gateway_call(system="ihms", operation="GET /api/products", headers=headers)
        try:
            response = await self._client.get(
                f"{self._base_url}/api/products",
                headers=headers.as_dict(),
            )
        except httpx.HTTPError as exc:
            raise map_transport_error(exc) from exc
        raise_for_ihms_response(response)
        data = response.json()
        if not isinstance(data, list):
            return []
        return [ProductCatalogItemResponse.model_validate(item) for item in data]

    async def get_inventory(self, headers: ObservabilityHeaders) -> list[InventoryItemResponse]:
        log_gateway_call(system="ihms", operation="GET /api/inventory", headers=headers)
        try:
            response = await self._client.get(
                f"{self._base_url}/api/inventory",
                headers=headers.as_dict(),
            )
        except httpx.HTTPError as exc:
            raise map_transport_error(exc) from exc
        raise_for_ihms_response(response)
        data = response.json()
        if not isinstance(data, list):
            return []
        return [InventoryItemResponse.model_validate(item) for item in data]

    async def fulfill_hold(
        self, hold_id: str, headers: ObservabilityHeaders
    ) -> HoldResponse | None:
        """Mark hold fulfilled — inventory stays deducted (sale committed)."""
        log_gateway_call(
            system="ihms",
            operation=f"POST /api/holds/{hold_id}/fulfill",
            headers=headers,
        )
        try:
            response = await self._client.post(
                f"{self._base_url}/api/holds/{hold_id}/fulfill",
                headers=headers.as_dict(),
            )
        except httpx.HTTPError as exc:
            raise map_transport_error(exc) from exc
        if response.status_code == 404:
            if self._fulfill_optional:
                return None
            raise_for_ihms_response(response)
        raise_for_ihms_response(response)
        if response.status_code == 204:
            return None
        return HoldResponse.model_validate(response.json())
