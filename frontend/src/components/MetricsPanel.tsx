import type { CounterfactualMetrics } from "../types/api";

interface MetricsPanelProps {
  metrics: CounterfactualMetrics;
}

function formatMetric(value: number | null) {
  return value === null ? "N/A" : value.toFixed(2);
}

export function MetricsPanel({ metrics }: MetricsPanelProps) {
  return (
    <div className="metrics-strip">
      <div>
        <span>Flip Success</span>
        <strong className={metrics.flip_success ? "metric-success" : "metric-danger"}>
          {metrics.flip_success ? "Yes" : "No"}
        </strong>
      </div>
      <div>
        <span>Words Changed</span>
        <strong>{metrics.search_calls + metrics.postprocess_calls}</strong>
      </div>
      <div>
        <span>Edit Distance</span>
        <strong>{formatMetric(metrics.token_edit_distance)}</strong>
      </div>
      <div>
        <span>Minimality</span>
        <strong>{formatMetric(metrics.fluency_score)}</strong>
      </div>
    </div>
  );
}
