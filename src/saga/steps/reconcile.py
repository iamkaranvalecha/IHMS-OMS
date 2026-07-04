"""Reconciliation step — resolve ambiguous EC-OPS order creation after timeout."""

import asyncio

from src.gateway.ecops_client import EcOpsClient
from src.gateway.ecops_models import OrderResponse
from src.gateway.exceptions import GatewayTimeoutError
from src.gateway.headers import ObservabilityHeaders


async def find_order_by_reference(
    ecops: EcOpsClient,
    client_reference: str,
    headers: ObservabilityHeaders,
    *,
    max_retries: int = 2,
) -> OrderResponse | None:
    """Query EC-OPS for an order created despite a timeout on POST /orders."""
    for attempt in range(max_retries + 1):
        try:
            order = await ecops.find_order_by_client_reference(client_reference, headers)
            if order is not None:
                return order
        except GatewayTimeoutError:
            if attempt >= max_retries:
                return None
        if attempt < max_retries:
            await asyncio.sleep(0.05 * (attempt + 1))
    return None
