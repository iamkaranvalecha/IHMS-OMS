# Observability

Structured identifiers propagate through the orchestrator. Upstream repos are unchanged — headers are logged if present.

## Identifier reference

| ID | Source | Propagation |
|----|--------|-------------|
| **Request ID** | Per HTTP request (`X-Request-ID`) | All orchestrator logs; response header |
| **Correlation ID** | Session create; stored on `CheckoutSession` | Gateway outbound headers; API responses |
| **Trace ID** | Per request span (`X-Trace-ID`) | Logs + gateway; aligns with future OpenTelemetry |
| **Hold ID** | IHMS `POST /api/holds` | Session + logs |
| **Order ID** | EC-OPS `POST /orders` | Session + logs |

## Structured log fields

```json
{
  "request_id": "uuid",
  "correlation_id": "uuid",
  "trace_id": "uuid",
  "hold_id": "optional",
  "order_id": "optional",
  "step": "place_hold | confirm | compensate | reconcile"
}
```

## Middleware (Phase 1)

`src/api/middleware.py` — `ObservabilityMiddleware` assigns IDs on every inbound request and echoes them on the response.

## Gateway outbound headers (Phase 2)

`IhmsClient` and `EcOpsClient` will forward:

- `X-Request-ID`
- `X-Correlation-ID`
- `X-Trace-ID`

## Future work

- OpenTelemetry SDK integration
- Log aggregation (JSON to stdout in Docker)
- Metrics: hold success rate, compensation count, reconciliation outcomes
