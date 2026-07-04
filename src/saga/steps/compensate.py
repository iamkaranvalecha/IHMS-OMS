"""Compensation step — release IHMS hold after order failure."""

import asyncio

from src.gateway.exceptions import (
    GatewayTimeoutError,
    HoldConflictError,
    HoldNotFoundError,
)
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient


async def release_hold_safe(
    ihms: IhmsClient,
    hold_id: str,
    headers: ObservabilityHeaders,
    *,
    max_retries: int = 2,
) -> bool:
    """Release a hold; return True when hold is gone or released.

    Treats 404/409 as success (idempotent release). Retries DELETE on timeout.
    """
    for attempt in range(max_retries + 1):
        try:
            await ihms.release_hold(hold_id, headers)
            return True
        except (HoldNotFoundError, HoldConflictError):
            return True
        except GatewayTimeoutError:
            if attempt >= max_retries:
                return False
            await asyncio.sleep(0.05 * (attempt + 1))
    return False
