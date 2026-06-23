from app.harness.target_predict import PredictionResult


class PredictionRepository:
    """In-memory prediction cache.

    TODO(P18-HARNESS-2): back this with the `predictions` SQLite table (see
    app/db/models.py) so the cache survives restarts. Cache key is built in
    PredictionService via app/db/hashing.py.
    """

    def __init__(self) -> None:
        self._cache: dict[str, PredictionResult] = {}

    def get(self, cache_key: str) -> PredictionResult | None:
        return self._cache.get(cache_key)

    def set(self, cache_key: str, result: PredictionResult) -> None:
        self._cache[cache_key] = result
