"""Unit tests for gateway HTTP error mapping."""

import httpx
import pytest
from src.gateway.exceptions import HoldConflictError, HoldNotFoundError, HoldValidationError
from src.gateway.http_utils import raise_for_ihms_response


def test_ihms_404_raises_hold_not_found() -> None:
    response = httpx.Response(404, json={"detail": "Hold not found"})
    with pytest.raises(HoldNotFoundError):
        raise_for_ihms_response(response)


def test_ihms_409_raises_hold_conflict() -> None:
    response = httpx.Response(409, json={"detail": "Hold expired"})
    with pytest.raises(HoldConflictError):
        raise_for_ihms_response(response)


def test_ihms_422_raises_validation() -> None:
    response = httpx.Response(422, json={"detail": "Quantity must be positive"})
    with pytest.raises(HoldValidationError):
        raise_for_ihms_response(response)
