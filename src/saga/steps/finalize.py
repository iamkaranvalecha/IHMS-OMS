"""Post-confirm hold finalization — commit sale without restoring inventory."""

import asyncio
import logging

from src.gateway.exceptions import (
    GatewayError,
    GatewayTimeoutError,
    HoldConflictError,
    HoldNotFoundError,
)
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient

logger = logging.getLogger(__name__)


async def fulfill_hold_safe(
    ihms: IhmsClient,
    hold_id: str,
    headers: ObservabilityHeaders,
    *,
    max_retries: int = 2,
) -> bool:
    """Best-effort fulfill after order success; retry on transient failures."""
    for attempt in range(max_retries + 1):
        try:
            await ihms.fulfill_hold(hold_id, headers)
            return True
        except (HoldNotFoundError, HoldConflictError):
            return True
        except GatewayTimeoutError:
            if attempt >= max_retries:
                logger.warning(
                    "hold fulfill timed out after order success",
                    extra={"hold_id": hold_id},
                )
                return False
            await asyncio.sleep(0.05 * (attempt + 1))
        except GatewayError:
            logger.warning(
                "hold fulfill failed after order success",
                extra={"hold_id": hold_id},
            )
            return False
    return False
