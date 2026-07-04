import type { ObservabilityIds } from "@/api/types";

interface DevObservabilityPanelProps {
  ids: ObservabilityIds | null;
}

export function DevObservabilityPanel({ ids }: DevObservabilityPanelProps) {
  if (!ids) {
    return (
      <aside className="dev-panel" aria-label="Developer observability">
        <h2>Dev panel</h2>
        <p className="muted">Observability IDs appear after the first API call.</p>
      </aside>
    );
  }

  return (
    <aside className="dev-panel" aria-label="Developer observability">
      <h2>Dev panel</h2>
      <dl>
        <div>
          <dt>Correlation ID</dt>
          <dd>{ids.correlationId ?? "—"}</dd>
        </div>
        <div>
          <dt>Trace ID</dt>
          <dd>{ids.traceId ?? "—"}</dd>
        </div>
        <div>
          <dt>Request ID</dt>
          <dd>{ids.requestId ?? "—"}</dd>
        </div>
      </dl>
    </aside>
  );
}
