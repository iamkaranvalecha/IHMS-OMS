"""KB-IHMS wire-format models (anti-corruption at gateway boundary)."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class HoldStatus(StrEnum):
    ACTIVE = "Active"
    RELEASED = "Released"
    EXPIRED = "Expired"


class CreateHoldItemRequest(BaseModel):
    product_id: str = Field(alias="productId")
    quantity: int

    model_config = {"populate_by_name": True}


class CreateHoldRequest(BaseModel):
    items: list[CreateHoldItemRequest]


class HoldItemResponse(BaseModel):
    product_id: str = Field(alias="productId")
    name: str
    quantity: int

    model_config = {"populate_by_name": True}


class HoldResponse(BaseModel):
    hold_id: str = Field(alias="holdId")
    status: HoldStatus
    items: list[HoldItemResponse]
    created_at: datetime = Field(alias="createdAt")
    expires_at: datetime = Field(alias="expiresAt")

    model_config = {"populate_by_name": True}
