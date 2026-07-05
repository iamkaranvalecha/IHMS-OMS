"""API route modules."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.deps import get_checkout_service
from src.api.errors import http_exception_for_error
from src.catalog.provider import CatalogProduct
from src.checkout.service import CheckoutService
from src.session.models import CheckoutSession

CheckoutDep = Annotated[CheckoutService, Depends(get_checkout_service)]

health_router = APIRouter(tags=["health"])
catalog_router = APIRouter(prefix="/catalog", tags=["catalog"])
sessions_router = APIRouter(prefix="/sessions", tags=["sessions"])


@health_router.get("/health")
async def health(request: Request) -> dict[str, str]:
    """Liveness probe with observability IDs echoed for debugging."""
    return {
        "status": "ok",
        "request_id": request.state.request_id,
        "correlation_id": request.state.correlation_id,
        "trace_id": request.state.trace_id,
    }


class CatalogProductOut(BaseModel):
    sku: str
    name: str
    ihms_product_id: str
    ecops_item_code: str
    unit_price: float

    @classmethod
    def from_catalog(cls, product: CatalogProduct) -> "CatalogProductOut":
        return cls(
            sku=product.sku,
            name=product.name,
            ihms_product_id=product.ihms_product_id,
            ecops_item_code=product.ecops_item_code,
            unit_price=product.unit_price,
        )


@catalog_router.get("", response_model=list[CatalogProductOut])
async def list_catalog(checkout: CheckoutDep) -> list[CatalogProductOut]:
    return [CatalogProductOut.from_catalog(p) for p in checkout.list_catalog()]


@catalog_router.get("/{sku}", response_model=CatalogProductOut)
async def get_catalog_product(
    sku: str,
    checkout: CheckoutDep,
) -> CatalogProductOut:
    product = checkout.get_product(sku)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {sku} not found")
    return CatalogProductOut.from_catalog(product)


class SessionCreateResponse(BaseModel):
    session_id: UUID
    correlation_id: str
    state: str


class SessionLineItemOut(BaseModel):
    sku: str
    name: str
    quantity: int
    unit_price: float


class SessionResponse(BaseModel):
    session_id: UUID
    correlation_id: str
    state: str
    hold_id: str | None = None
    order_id: str | None = None
    expires_at: str | None = None
    customer_name: str | None = None
    line_items: list[SessionLineItemOut] = Field(default_factory=list)

    @classmethod
    def from_session(cls, session: CheckoutSession) -> "SessionResponse":
        return cls(
            session_id=session.session_id,
            correlation_id=session.correlation_id,
            state=session.state.value,
            hold_id=session.hold_id,
            order_id=session.order_id,
            expires_at=session.expires_at.isoformat() if session.expires_at else None,
            customer_name=session.customer_name,
            line_items=[
                SessionLineItemOut(
                    sku=item.sku,
                    name=item.name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                for item in session.line_items
            ],
        )


class SessionCreateBody(BaseModel):
    correlation_id: str | None = Field(
        default=None,
        description="Optional; defaults to request correlation ID",
    )


class PlaceHoldBody(BaseModel):
    sku: str = Field(min_length=1)
    quantity: int = Field(gt=0, default=1)
    customer_name: str = Field(min_length=1)


class ConfirmBody(BaseModel):
    customer_name: str | None = Field(
        default=None,
        description="Optional if set during place-hold",
    )


@sessions_router.post("", response_model=SessionCreateResponse, status_code=201)
async def create_session(
    request: Request,
    checkout: CheckoutDep,
    body: SessionCreateBody | None = None,
) -> SessionCreateResponse:
    correlation_id = (body.correlation_id if body and body.correlation_id else None) or (
        request.state.correlation_id
    )
    session = checkout.create_session(correlation_id)
    return SessionCreateResponse(
        session_id=session.session_id,
        correlation_id=session.correlation_id,
        state=session.state.value,
    )


@sessions_router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    checkout: CheckoutDep,
) -> SessionResponse:
    session = checkout.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse.from_session(session)


@sessions_router.post("/{session_id}/hold", response_model=SessionResponse)
async def place_hold(
    session_id: UUID,
    body: PlaceHoldBody,
    request: Request,
    checkout: CheckoutDep,
) -> SessionResponse:
    session = checkout.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    headers = checkout.observability_for_session(
        session,
        request.state.request_id,
        request.state.trace_id,
    )
    try:
        session = await checkout.place_hold(
            session_id,
            body.sku,
            body.quantity,
            body.customer_name,
            headers,
        )
    except Exception as exc:
        raise http_exception_for_error(exc) from exc
    return SessionResponse.from_session(session)


@sessions_router.post("/{session_id}/confirm", response_model=SessionResponse)
async def confirm_session(
    session_id: UUID,
    request: Request,
    checkout: CheckoutDep,
    body: ConfirmBody | None = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> SessionResponse:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")
    session = checkout.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    headers = checkout.observability_for_session(
        session,
        request.state.request_id,
        request.state.trace_id,
    )
    customer_name = body.customer_name if body else None
    try:
        result = await checkout.confirm(session_id, customer_name, idempotency_key, headers)
    except Exception as exc:
        raise http_exception_for_error(exc) from exc
    return SessionResponse.from_session(result.session)


@sessions_router.delete("/{session_id}", response_model=SessionResponse)
async def abandon_session(
    session_id: UUID,
    request: Request,
    checkout: CheckoutDep,
) -> SessionResponse:
    session = checkout.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    headers = checkout.observability_for_session(
        session,
        request.state.request_id,
        request.state.trace_id,
    )
    try:
        session = await checkout.abandon(session_id, headers)
    except Exception as exc:
        raise http_exception_for_error(exc) from exc
    return SessionResponse.from_session(session)
