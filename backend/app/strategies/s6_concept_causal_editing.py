from app.core.config import get_settings
from app.proposer.concepts import (
    CONCEPT_CLASSES,
    apply_concept_edit,
    describe_concept_edit,
)
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
STRATEGY_ID = "s6_concept_causal_editing"


class S6ConceptCausalEditingStrategy(CounterfactualStrategy):
    """S6: propose one typed concept intervention, then verify the frozen target."""

    id = STRATEGY_ID
    name = "S6 Concept-level Causal Editing"

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
            if count <= 0:
                break
            proposals = proposer.propose_concept_edits(
                scenario,
                choices,
                foil,
                count=count,
                allowed_concepts=CONCEPT_CLASSES,
                avoid=recent_rejects[-AVOID_WINDOW:],
            )[:remaining_budget]

            for proposed_edit in proposals:
                if len(attempts) >= budget:
                    break

                description = describe_concept_edit(proposed_edit)
                applied = apply_concept_edit(scenario, proposed_edit)
                if applied is None:
                    recent_rejects.append(description)
                    continue

                modified_scenario, resolved_edit = applied
                description = describe_concept_edit(resolved_edit)
                key = normalise_key(modified_scenario)
                if not key or key in seen:
                    recent_rejects.append(description)
                    continue

                seen.add(key)
                if is_degenerate_foil_leak(modified_scenario, foil_text):
                    recent_rejects.append(description)
                    continue

                if exceeds_changed_fraction(
                    scenario,
                    modified_scenario,
                    self._max_changed_fraction,
                ):
                    recent_rejects.append(description)
                    continue

                prediction = model.target_predict(modified_scenario, choices)
                success = prediction.answer == foil
                edit_description = description
                if resolved_edit.rationale:
                    edit_description = f"{description}; {resolved_edit.rationale}"
                attempts.append(
                    AttemptRecord(
                        modified_scenario=modified_scenario,
                        prediction=prediction,
                        success=success,
                        edit_description=edit_description,
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
                        concept_edit=resolved_edit,
                    )

                recent_rejects.append(description)

        return CounterfactualResult(
            status="not_found",
            original_scenario=scenario,
            modified_scenario=None,
            new_answer=None,
            foil=foil,
            strategy_id=self.id,
            attempts=attempts,
            message="no S6 concept edit flipped the scenario within budget",
        )
