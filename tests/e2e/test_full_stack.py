"""End-to-end tests — require compose.full.yml stack (STACK=1)."""

import pytest


@pytest.mark.e2e
def test_e2e_scaffold_skipped_by_default() -> None:
    """Placeholder until Phase 5 full stack is available."""
    assert True
