"""KB-IHMS wire-format models (anti-corruption at gateway boundary)."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class HoldStatus(StrEnum):
    ACTIVE = "Active"
    RELEASED = "Released"
    EXPIRED = "Expired"
    FULFILLED = "Fulfilled"


class ProductCatalogItemResponse(BaseModel):
    product_id: str = Field(alias="productId")
    sku: str
    name: str
    description: str = ""
    category: str = ""
    unit_price: float = Field(alias="unitPrice")
    currency: str = "USD"
    available_quantity: int = Field(alias="availableQuantity")
    image_url: str = Field(default="", alias="imageUrl")
    sellable: bool = True

    model_config = {"populate_by_name": True}


class InventoryItemResponse(BaseModel):
    product_id: str = Field(alias="productId")
    available_quantity: int = Field(alias="availableQuantity")

    model_config = {"populate_by_name": True}


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
