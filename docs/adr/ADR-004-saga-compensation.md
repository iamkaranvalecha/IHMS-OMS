# ADR-004: Saga with Compensation

**Status:** Accepted  
**Date:** 2026-07-04

## Context

Checkout spans two services without a distributed transaction manager. Hold-then-order can leave inconsistent state if order creation fails.

## Decision

Implement saga pattern in `src/saga/` with explicit compensation: release IHMS hold when EC-OPS order fails.

## Consequences

- No two-phase commit required.
- Compensation path is first-class (see `sequences/compensation.md`).
- Idempotency required on confirm to handle retries safely.
