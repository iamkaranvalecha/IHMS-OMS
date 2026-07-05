"""Unit tests for saga metrics registry."""

import pytest
from src.observability.metrics import MetricsRegistry, get_metrics_registry


def test_metrics_increment_and_snapshot() -> None:
    registry = MetricsRegistry()
    registry.increment("holds_placed_total")
    registry.increment("holds_placed_total")
    registry.increment("compensations_total")

    snapshot = registry.snapshot()
    assert snapshot["holds_placed_total"] == 2
    assert snapshot["compensations_total"] == 1
    assert snapshot["confirms_success_total"] == 0


def test_metrics_prometheus_format() -> None:
    registry = MetricsRegistry()
    registry.increment("confirms_reconciled_total")
    body = registry.to_prometheus()
    assert "confirms_reconciled_total 1" in body
    assert "# TYPE confirms_reconciled_total counter" in body


def test_metrics_unknown_counter_raises() -> None:
    registry = MetricsRegistry()
    with pytest.raises(ValueError, match="Unknown counter"):
        registry.increment("not_a_counter")


def test_global_registry_increment() -> None:
    get_metrics_registry().increment("abandons_total")
    assert get_metrics_registry().snapshot()["abandons_total"] == 1
