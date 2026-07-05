"""Unit tests for fulfill hold finalization."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.gateway.exceptions import GatewayTimeoutError
from src.gateway.headers import ObservabilityHeaders
from src.saga.steps.finalize import fulfill_hold_safe

OBS = ObservabilityHeaders(request_id="r1", correlation_id="c1", trace_id="t1")


@pytest.mark.asyncio
async def test_fulfill_hold_safe_retries_on_timeout() -> None:
    ihms = MagicMock()
    ihms.fulfill_hold = AsyncMock(
        side_effect=[GatewayTimeoutError("timeout"), None],
    )

    result = await fulfill_hold_safe(ihms, "hold-1", OBS, max_retries=2)

    assert result is True
    assert ihms.fulfill_hold.await_count == 2


@pytest.mark.asyncio
async def test_fulfill_hold_safe_returns_false_after_exhausted_timeouts() -> None:
    ihms = MagicMock()
    ihms.fulfill_hold = AsyncMock(side_effect=GatewayTimeoutError("timeout"))

    result = await fulfill_hold_safe(ihms, "hold-1", OBS, max_retries=1)

    assert result is False
    assert ihms.fulfill_hold.await_count == 2
