"""Confirm idempotency store — deduplicate retries and double-clicks."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class IdempotencyRecord:
    """Cached confirm response keyed by (session_id, idempotency_key)."""

    status_code: int
    body: dict[str, object]
    order_id: str | None = None


class IdempotencyStore(Protocol):
    def get(self, session_id: UUID, key: str) -> IdempotencyRecord | None: ...

    def put(self, session_id: UUID, key: str, record: IdempotencyRecord) -> None: ...


class InMemoryIdempotencyStore:
    """In-memory idempotency cache for Phase 3."""

    def __init__(self) -> None:
        self._records: dict[tuple[UUID, str], IdempotencyRecord] = {}

    def get(self, session_id: UUID, key: str) -> IdempotencyRecord | None:
        return self._records.get((session_id, key))

    def put(self, session_id: UUID, key: str, record: IdempotencyRecord) -> None:
        self._records[(session_id, key)] = record
