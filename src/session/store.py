"""Checkout session persistence."""

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
