"""In-process saga metrics for demos and health monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

_COUNTERS = (
    "holds_placed_total",
    "holds_failed_total",
    "confirms_success_total",
    "confirms_reconciled_total",
    "compensations_total",
    "abandons_total",
    "order_status_unknown_total",
)


@dataclass
class MetricsRegistry:
    """Thread-safe counters for checkout saga outcomes."""

    holds_placed_total: int = 0
    holds_failed_total: int = 0
    confirms_success_total: int = 0
    confirms_reconciled_total: int = 0
    compensations_total: int = 0
    abandons_total: int = 0
    order_status_unknown_total: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    def increment(self, counter: str, amount: int = 1) -> None:
        if counter not in _COUNTERS:
            raise ValueError(f"Unknown counter: {counter}")
        with self._lock:
            setattr(self, counter, getattr(self, counter) + amount)

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {name: getattr(self, name) for name in _COUNTERS}

    def to_prometheus(self) -> str:
        lines: list[str] = []
        for name in _COUNTERS:
            value = self.snapshot()[name]
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        return "\n".join(lines) + "\n"


_registry = MetricsRegistry()


def get_metrics_registry() -> MetricsRegistry:
    return _registry


def reset_metrics_registry() -> None:
    """Reset counters — for tests only."""
    global _registry
    _registry = MetricsRegistry()
