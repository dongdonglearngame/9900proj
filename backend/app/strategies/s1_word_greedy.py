from collections.abc import Iterable

from app.strategies.base import (
    AttemptRecord,
    CounterfactualRequest,
    CounterfactualResult,
    CounterfactualStrategy,
    TargetPredictFn,
)

PHRASE_REPLACEMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("middle of the night", ("early evening", "afternoon")),
    ("late at night", ("early evening", "afternoon")),
    ("very late", ("earlier",)),
    ("urgent", ("not urgent",)),
    ("furious", ("upset",)),
    ("very angry", ("slightly upset",)),
    ("angry", ("upset",)),
    ("lonely", ("calm",)),
    ("devastated", ("sad",)),
    ("extremely upset", ("upset",)),
)


class S1WordGreedyStrategy(CounterfactualStrategy):
    """S1 word-level greedy baseline.

    The strategy proposes deterministic, local phrase replacements, deduplicates
    candidates, and lets the shared target harness decide whether a flip happened.
    """

    id = "s1_word_greedy"
    name = "S1 Word-level Greedy"

    def generate(
        self,
        request: CounterfactualRequest,
        target_predict: TargetPredictFn,
    ) -> CounterfactualResult:
        attempts: list[AttemptRecord] = []
        budget = max(request.budget, 0)

        for modified_scenario, description in self._generate_candidates(request.scenario):
            if len(attempts) >= budget:
                break

            prediction = target_predict(modified_scenario, request.choices, request.model)
            success = prediction.answer == request.foil
            attempts.append(
                AttemptRecord(
                    modified_scenario=modified_scenario,
                    prediction=prediction,
                    success=success,
                    edit_description=description,
                )
            )

            if success:
                return CounterfactualResult(
                    status="success",
                    original_scenario=request.scenario,
                    modified_scenario=modified_scenario,
                    original_answer=request.original_answer,
                    new_answer=prediction.answer,
                    foil=request.foil,
                    strategy_id=self.id,
                    attempts=attempts,
                    message=None,
                )

        return CounterfactualResult(
            status="not_found",
            original_scenario=request.scenario,
            modified_scenario=None,
            original_answer=request.original_answer,
            new_answer=None,
            foil=request.foil,
            strategy_id=self.id,
            attempts=attempts,
            message="no S1 candidate flipped the factual scenario within budget",
        )

    def _generate_candidates(self, scenario: str) -> Iterable[tuple[str, str]]:
        seen: set[str] = set()
        lower = scenario.lower()

        for source, replacements in PHRASE_REPLACEMENTS:
            start = 0
            while True:
                index = lower.find(source, start)
                if index == -1:
                    break

                original_span = scenario[index : index + len(source)]
                for replacement in replacements:
                    candidate = (
                        scenario[:index]
                        + _match_initial_case(original_span, replacement)
                        + scenario[index + len(source) :]
                    )
                    if candidate == scenario or candidate in seen:
                        continue
                    seen.add(candidate)
                    yield candidate, f"replace '{original_span}' with '{replacement}'"

                start = index + len(source)


def _match_initial_case(original: str, replacement: str) -> str:
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement
