"""EC-OPS wire-format models."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class OrderItemCreate(BaseModel):
    product_name: str
    quantity: int = Field(gt=0)
    price: Decimal = Field(ge=Decimal("0"))


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1)
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemResponse(BaseModel):
    id: UUID
    order_id: UUID
    product_name: str
    quantity: int
    price: Decimal


class OrderResponse(BaseModel):
    id: UUID
    customer_name: str
    status: OrderStatus
    created_at: datetime
    updated_at: datetime | None
    items: list[OrderItemResponse]
    client_reference: str | None = None
