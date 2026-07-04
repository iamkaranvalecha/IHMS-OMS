# ADR-006: Request + Correlation + Trace ID Propagation

**Status:** Accepted  
**Date:** 2026-07-04

## Context

Distributed checkout requires correlating UI actions, orchestrator steps, and upstream calls across failure and reconciliation paths.

## Decision

Propagate three identifiers:

- `X-Request-ID` — per inbound HTTP request
- `X-Correlation-ID` — checkout session scope
- `X-Trace-ID` — per span; OpenTelemetry-compatible future path

## Consequences

- Middleware in `src/api/middleware.py` assigns IDs Phase 1.
- Gateway forwards headers Phase 2.
- Structured logs include `{ request_id, correlation_id, trace_id, hold_id, order_id, step }`.

See [OBSERVABILITY.md](../OBSERVABILITY.md).
