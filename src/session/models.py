"""Checkout session domain model."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SessionState(StrEnum):
    CREATED = "CREATED"
    HELD = "HELD"
    CONFIRMED = "CONFIRMED"
    ABANDONED = "ABANDONED"
    COMPENSATED = "COMPENSATED"
    RECONCILED = "RECONCILED"


class CheckoutSession(BaseModel):
    """Orchestrator checkout session persisted across saga steps."""

    session_id: UUID = Field(default_factory=uuid4)
    correlation_id: str
    state: SessionState = SessionState.CREATED
    hold_id: str | None = None
    order_id: str | None = None
    expires_at: datetime | None = None
    idempotency_key: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
