from app.schemas.metrics import CounterfactualMetrics


class MetricsRepository:
    """In-memory store of per-result metrics.

    TODO(P18-METRICS-1): persist to the `metrics` table and add a summary() aggregation
    for the comparison dashboard (flip_rate, avg edit distance, avg search calls, ...).
    """

    def __init__(self) -> None:
        self._metrics: list[CounterfactualMetrics] = []

    def add(self, metrics: CounterfactualMetrics) -> None:
        self._metrics.append(metrics)

    def list_metrics(self) -> list[CounterfactualMetrics]:
        return list(self._metrics)
