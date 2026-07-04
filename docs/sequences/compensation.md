# Sequence: Compensation

**Use case:** UC-6 variant — order fails after successful hold

**Status:** Implemented (Phase 3)

## Flow

```mermaid
sequenceDiagram
  participant API as Orchestrator
  participant IHMS as KB-IHMS
  participant OPS as EC-OPS

  Note over API: Hold already placed

  API->>OPS: POST /orders
  OPS-->>API: 4xx/5xx

  API->>IHMS: DELETE /api/holds/{hold_id}
  IHMS-->>API: 204
  Note over API: Session → COMPENSATED
```

## Saga rule

Compensation is mandatory. Never leave an orphaned hold after order failure.

See [ADR-004](../adr/ADR-004-saga-compensation.md).
