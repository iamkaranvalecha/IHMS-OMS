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


class SessionLineItem(BaseModel):
    """Frozen catalog mapping captured at hold time."""

    sku: str
    name: str
    ihms_product_id: str
    ecops_item_code: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)


class CheckoutSession(BaseModel):
    """Orchestrator checkout session persisted across saga steps."""

    session_id: UUID = Field(default_factory=uuid4)
    correlation_id: str
    state: SessionState = SessionState.CREATED
    hold_id: str | None = None
    order_id: str | None = None
    expires_at: datetime | None = None
    idempotency_key: str | None = None
    customer_name: str | None = None
    line_items: list[SessionLineItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def is_terminal(self) -> bool:
        return self.state in {
            SessionState.CONFIRMED,
            SessionState.ABANDONED,
            SessionState.COMPENSATED,
            SessionState.RECONCILED,
        }
