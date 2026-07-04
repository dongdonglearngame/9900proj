from app.core.config import get_settings
from app.strategies._candidate_filters import (
    exceeds_changed_fraction,
    is_degenerate_foil_leak,
    normalise_key,
)
from app.strategies.base import (
    AttemptRecord,
    CounterfactualResult,
    CounterfactualStrategy,
    Proposer,
    TargetModel,
)

AVOID_WINDOW = 8


class S2LlmProposeVerifyStrategy(CounterfactualStrategy):
    """S2: ask a proposer LLM for candidate edits, then verify with the frozen target."""

    id = "s2_llm_propose_verify"
    name = "S2 LLM Propose-Verify"

    def __init__(
        self,
        *,
        candidates_per_round: int | None = None,
        max_rounds: int | None = None,
        max_changed_fraction: float | None = None,
    ) -> None:
        settings = get_settings()
        self._candidates_per_round = (
            candidates_per_round
            if candidates_per_round is not None
            else settings.proposer_candidates_per_round
        )
        self._max_rounds = max_rounds if max_rounds is not None else settings.proposer_max_rounds
        self._max_changed_fraction = (
            max_changed_fraction
            if max_changed_fraction is not None
            else settings.proposer_max_changed_fraction
        )

    def generate(
        self,
        scenario: str,
        choices: dict[str, str],
        model: TargetModel,
        foil: str,
        budget: int,
        proposer: Proposer,
    ) -> CounterfactualResult:
        attempts: list[AttemptRecord] = []
        budget = max(budget, 0)
        seen = {normalise_key(scenario)}
        recent_rejects: list[str] = []
        foil_text = choices[foil]
        rounds = 0

        while len(attempts) < budget and rounds < self._max_rounds:
            rounds += 1
            remaining_budget = budget - len(attempts)
            count = min(self._candidates_per_round, remaining_budget)
            proposals = proposer.propose(
                scenario,
                choices,
                foil,
                count=count,
                avoid=recent_rejects[-AVOID_WINDOW:],
            )[:remaining_budget]

            for edit in proposals:
                if len(attempts) >= budget:
                    break

                modified_scenario = edit.modified_scenario.strip()
                key = normalise_key(modified_scenario)
                if not key or key in seen:
                    continue

                if is_degenerate_foil_leak(modified_scenario, foil_text):
                    seen.add(key)
                    recent_rejects.append(modified_scenario)
                    continue

                if exceeds_changed_fraction(
                    scenario,
                    modified_scenario,
                    self._max_changed_fraction,
                ):
                    seen.add(key)
                    continue

                seen.add(key)
                prediction = model.target_predict(modified_scenario, choices)
                success = prediction.answer == foil
                attempts.append(
                    AttemptRecord(
                        modified_scenario=modified_scenario,
                        prediction=prediction,
                        success=success,
                        edit_description=edit.rationale,
                    )
                )

                if success:
                    return CounterfactualResult(
                        status="success",
                        original_scenario=scenario,
                        modified_scenario=modified_scenario,
                        new_answer=prediction.answer,
                        foil=foil,
                        strategy_id=self.id,
                        attempts=attempts,
                        message=None,
                    )

                recent_rejects.append(modified_scenario)

        return CounterfactualResult(
            status="not_found",
            original_scenario=scenario,
            modified_scenario=None,
            new_answer=None,
            foil=foil,
            strategy_id=self.id,
            attempts=attempts,
            message="no S2 proposal flipped the scenario within budget",
        )
