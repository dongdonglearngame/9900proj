import type { CounterfactualMetrics } from "../types/api";

interface MetricsPanelProps {
  metrics: CounterfactualMetrics;
}

function formatMetric(value: number | null) {
  return value === null ? "N/A" : value.toFixed(2);
}

function formatCount(value: number | null) {
  return value === null ? "N/A" : value.toString();
}

function formatPercent(value: number | null) {
  return value === null ? "N/A" : `${(value * 100).toFixed(1)}%`;
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
        <strong>{formatCount(metrics.token_edit_distance)}</strong>
      </div>
      <div>
        <span>Model Calls</span>
        <strong>{metrics.total_target_calls}</strong>
      </div>
      <div>
        <span>Minimality</span>
        <strong>{formatPercent(metrics.changed_word_fraction)}</strong>
      </div>
    </div>
  );
}
