"""Checkout session persistence."""

import asyncio
from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from src.session.models import CheckoutSession


class SessionStore(Protocol):
    def save(self, session: CheckoutSession) -> CheckoutSession: ...

    def get(self, session_id: UUID) -> CheckoutSession | None: ...


class InMemorySessionStore:
    """In-memory session store for Phase 1–3."""

    def __init__(self) -> None:
        self._sessions: dict[UUID, CheckoutSession] = {}

    def save(self, session: CheckoutSession) -> CheckoutSession:
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: UUID) -> CheckoutSession | None:
        return self._sessions.get(session_id)


class LockedSessionStore:
    """Wraps a session store with per-session asyncio locks for saga mutations."""

    def __init__(self, inner: SessionStore) -> None:
        self._inner = inner
        self._locks: dict[UUID, asyncio.Lock] = {}

    def _lock_for(self, session_id: UUID) -> asyncio.Lock:
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    def lock_for(self, session_id: UUID) -> asyncio.Lock:
        """Return the per-session lock for operations with upstream side effects."""
        return self._lock_for(session_id)

    def save(self, session: CheckoutSession) -> CheckoutSession:
        return self._inner.save(session)

    def get(self, session_id: UUID) -> CheckoutSession | None:
        return self._inner.get(session_id)

    async def mutate(
        self,
        session_id: UUID,
        mutator: Callable[[CheckoutSession], CheckoutSession],
    ) -> CheckoutSession:
        async with self._lock_for(session_id):
            session = self._inner.get(session_id)
            if session is None:
                msg = "Session not found"
                raise KeyError(msg)
            updated = mutator(session)
            return self._inner.save(updated)
