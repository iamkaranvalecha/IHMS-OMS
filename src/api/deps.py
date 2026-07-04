"""FastAPI dependencies."""

from fastapi import Request

from src.checkout.service import CheckoutService


def get_checkout_service(request: Request) -> CheckoutService:
    return request.app.state.checkout_service
