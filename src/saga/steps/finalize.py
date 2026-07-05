"""Post-confirm hold finalization — commit sale without restoring inventory."""

import logging

from src.gateway.exceptions import GatewayError, HoldNotFoundError
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient

logger = logging.getLogger(__name__)


async def fulfill_hold_safe(
    ihms: IhmsClient,
    hold_id: str,
    headers: ObservabilityHeaders,
) -> bool:
    """Best-effort fulfill after order success; do not fail confirm if unavailable."""
    try:
        await ihms.fulfill_hold(hold_id, headers)
        return True
    except HoldNotFoundError:
        return True
    except GatewayError:
        logger.warning(
            "hold fulfill failed after order success",
            extra={"hold_id": hold_id},
        )
        return False
