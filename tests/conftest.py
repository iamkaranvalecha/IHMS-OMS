"""Shared pytest fixtures."""

import pytest
from src.observability.metrics import reset_metrics_registry


@pytest.fixture(autouse=True)
def _reset_metrics_between_tests() -> None:
    reset_metrics_registry()
