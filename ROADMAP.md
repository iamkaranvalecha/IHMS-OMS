# ROADMAP

Volatile phase tracking. Update when a phase gate passes — not in AGENTS.md.

**Project board:** [GitHub Project #5](https://github.com/users/iamkaranvalecha/projects/5/views/1)

---

## Current phase: Complete — Phase 6 gate passed (2026-07-05)

**Goal achieved:** JSON structured logs, saga step logging, `/metrics` counters, observability tests.

---

## Completed

| Phase | Gate passed | Notes |
|-------|-------------|-------|
| Phase 0 | 2026-07-04 | KB-IHMS CI green; EC-OPS main CI red (frozen) |
| Phase 1 | 2026-07-04 | Scaffold — verify.sh, docs, 4 rules, CI |
| Phase 2 | 2026-07-04 | IhmsClient, EcOpsClient, session store, catalog API, 18 tests |
| Phase 3 | 2026-07-04 | Saga coordinator, hold/confirm/cancel, compensation, idempotency, reconciliation |
| Phase 4 | 2026-07-04 | React UI — catalog, cart, countdown, confirm/abandon, dev panel, Vitest |
| Phase 5 | 2026-07-05 | Mock upstreams, compose.full.yml, E2E suite, CI e2e job |
| Phase 6 | 2026-07-05 | JSON logs, saga metrics, `/metrics`, observability tests |

### Phase 6 deliverables

- [x] JSON structured logs (`src/observability/logging.py`)
- [x] Request context binding in middleware
- [x] Saga step logs + Prometheus counters
- [x] `GET /metrics` endpoint
- [x] Unit + integration observability tests
- [x] OBSERVABILITY.md updated; version 0.6.0

---

## Next

Future work (post v1 integration):

- OpenTelemetry SDK + OTLP export
- Real upstream smoke job (Lane 2)
- Persistent session store (Redis)
- Swap mock upstreams for published images in demo environments
