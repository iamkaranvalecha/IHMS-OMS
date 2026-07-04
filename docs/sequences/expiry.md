# Sequence: Hold Expiry

**Use case:** UC-7 (hold expires before confirm)

**Status:** Stub — finalize in Phase 3

## Flow

```mermaid
sequenceDiagram
  participant UI
  participant API as Orchestrator
  participant IHMS as KB-IHMS

  Note over UI,IHMS: Hold TTL elapsed

  UI->>API: POST /sessions/{id}/confirm
  API->>IHMS: POST /api/holds (or validate existing)
  IHMS-->>API: 409 Hold expired
  API-->>UI: 409 Cannot confirm — hold expired
```

## UI behaviour

- Countdown timer from `expires_at` returned at hold time.
- Disable confirm button when expired; offer restart checkout.
