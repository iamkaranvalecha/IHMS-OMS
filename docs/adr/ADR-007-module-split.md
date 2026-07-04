# ADR-007: Internal Module Split

**Status:** Accepted  
**Date:** 2026-07-04

## Context

Monolithic orchestrator code would blur boundaries between HTTP handling, saga logic, and upstream I/O.

## Decision

Split into six modules with strict dependency direction:

```
api → checkout → saga + session + catalog → gateway
```

## Consequences

- Gateway is the only upstream HTTP caller.
- Component tests can wire modules without real IHMS/EC-OPS.
- Session storage starts in-memory; Redis noted as scale path without module rename.
