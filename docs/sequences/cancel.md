# Sequence: Cancel / Abandon

**Use case:** UC-6 (abandon checkout)

**Status:** Stub — finalize in Phase 3

## Flow

```mermaid
sequenceDiagram
  participant UI
  participant API as Orchestrator
  participant IHMS as KB-IHMS

  UI->>API: DELETE /sessions/{id}
  API->>IHMS: DELETE /api/holds/{hold_id}
  IHMS-->>API: 204
  API-->>UI: abandoned
```

## Notes

- Only applicable when session is in `HELD` state.
- If no hold was placed, transition directly to `ABANDONED`.
