# Observability

Structured identifiers and logs propagate through the orchestrator. Upstream repos are unchanged — headers are logged if present.

## Identifier reference

| ID | Source | Propagation |
|----|--------|-------------|
| **Request ID** | Per HTTP request (`X-Request-ID`) | All orchestrator logs; response header |
| **Correlation ID** | Session scope (`CheckoutSession.correlation_id`) | Gateway outbound headers on saga steps; API responses |
| **Trace ID** | Per request span (`X-Trace-ID`) | Logs + gateway; OpenTelemetry-ready |
| **Hold ID** | IHMS `POST /api/holds` | Session + saga logs |
| **Order ID** | EC-OPS `POST /orders` | Session + saga logs |

## Structured log fields

Every JSON log line includes:

```json
{
  "timestamp": "2026-07-05T12:00:00+00:00",
  "level": "INFO",
  "logger": "checkout.saga",
  "message": "hold placed",
  "request_id": "uuid",
  "correlation_id": "uuid",
  "trace_id": "uuid",
  "session_id": "uuid",
  "hold_id": "optional",
  "order_id": "optional",
  "step": "place_hold | confirm | reconcile | compensate | abandon | http_request",
  "outcome": "success | failed | cached | ..."
}
```

Configure via environment:

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOG_LEVEL` | `INFO` | Root log level |
| `LOG_JSON` | `true` | JSON vs plain text |

Docker Compose sets these via `x-orchestrator-env` in `docker/compose.base.yml`. Orchestrator logs are JSON lines on stdout; use `docker compose logs orchestrator` or `bash scripts/e2e-stack.sh logs orchestrator`.

## Docker observability stack

Prometheus scrapes orchestrator saga counters:

```bash
bash scripts/obs-stack.sh up
# orchestrator metrics: http://localhost:8000/metrics
# Prometheus UI:        http://localhost:9090
# UI proxied metrics:   http://localhost:5173/metrics
bash scripts/obs-stack.sh down
```

Compose files:

| File | Purpose |
|------|---------|
| `docker/compose.base.yml` | Shared networks/volumes |
| `docker/compose.full.yml` | Mock upstreams + full stack (CI Lane 1b) |
| `docker/compose.upstream.yml` | Real upstreams on host (Lane 2 external) |
| `docker/compose.bundle.yml` | Bundled KB-IHMS + EC-OPS siblings |
| `docker/compose.observability.yml` | Prometheus (`--profile obs`) |
| `docker/prometheus/prometheus.yml` | Scrape target `orchestrator:8000/metrics` |

## Middleware

`src/api/middleware.py` — `ObservabilityMiddleware` assigns IDs, binds log context, and emits `http_request` log lines with duration and status.

## Saga logging

`src/observability/saga_events.py` — saga coordinator emits step logs and increments metrics at hold, confirm, reconcile, compensate, and abandon.

## Metrics

`GET /metrics` — Prometheus text format counters:

| Counter | When incremented |
|---------|------------------|
| `holds_placed_total` | Successful hold |
| `holds_failed_total` | IHMS hold rejected |
| `confirms_success_total` | Confirm or reconcile success |
| `confirms_reconciled_total` | Confirm after timeout reconciliation |
| `compensations_total` | Hold released after order failure |
| `abandons_total` | Session abandoned |
| `order_status_unknown_total` | Ambiguous order status; hold retained |

## Gateway outbound headers

`IhmsClient` and `EcOpsClient` forward:

- `X-Request-ID`
- `X-Correlation-ID` (session correlation on saga steps)
- `X-Trace-ID`

## Future work

- OpenTelemetry SDK + OTLP exporter (`OTEL_ENABLED`)
- Log aggregation sidecar in compose.full.yml
- Grafana dashboard for `/metrics` scrape
