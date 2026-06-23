from app.schemas.counterfactual import CounterfactualResultPayload


class CounterfactualRepository:
    """In-memory store of completed counterfactual results.

    TODO(P18-CF-2): persist to the `counterfactuals` table (see app/db/models.py).
    """

    def __init__(self) -> None:
        self._results: list[CounterfactualResultPayload] = []

    def add(self, result: CounterfactualResultPayload) -> None:
        self._results.append(result)

    def list_results(self) -> list[CounterfactualResultPayload]:
        return list(self._results)
