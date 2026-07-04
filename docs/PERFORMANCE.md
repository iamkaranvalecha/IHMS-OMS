# Performance

Phase 1 policies. Update this document when timeout or retry values change.

## Retry policy

| Operation | Retries | Notes |
|-----------|---------|-------|
| Idempotent GET (reconciliation query) | Up to 2 with backoff | Safe to repeat |
| POST without idempotency key | **No blind retry** | Risk of duplicate side effects |
| POST with idempotency key | **No blind retry unless upstream enforces idempotency** | Frozen EC-OPS ignores the header, so retry risks duplicates |

## Timeout policy (planned Phase 2)

| Upstream | Connect | Read | Rationale |
|----------|---------|------|-----------|
| KB-IHMS | 2s | 5s | Hold operations should be fast |
| EC-OPS | 2s | 10s | Order creation may include DB work |

Values are initial defaults — tune with integration test evidence.

## Connection pooling

- Single shared `httpx.AsyncClient` per upstream in gateway lifespan.
- Reuse across requests; close on app shutdown.

## Async I/O

FastAPI + async gateway throughout. No blocking I/O in request path.

## Session storage

| Phase | Storage | Notes |
|-------|---------|-------|
| 1–3 | In-memory dict | Single-process dev/demo |
| Scale path | Redis | See ADR-007; not required Phase 1 |

## Circuit breaker

Documented as future enhancement. Not required for Phase 1–3.

## Load testing

Deferred to Phase 5 E2E baseline. Target: p95 confirm latency under composed stack.
