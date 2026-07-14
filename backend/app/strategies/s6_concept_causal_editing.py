from dataclasses import replace

from app.core.config import get_settings
from app.proposer.concepts import (
    CONCEPT_CLASSES,
    apply_concept_edit,
    concept_edit_key,
    concept_span_key,
    describe_concept_edit,
    normalise_concept_text,
)
from app.proposer.harness import CandidateOutcome, record_candidate_outcome
from app.strategies._candidate_filters import (
    exceeds_changed_fraction,
    is_degenerate_foil_leak,
    normalise_key,
)
from app.strategies.base import (
    AttemptRecord,
    ConceptEdit,
    ConceptEditKey,
    CounterfactualResult,
    CounterfactualStrategy,
    Proposer,
    TargetModel,
)

AVOID_WINDOW = 8
MAX_REPAIR_CALLS = 1
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
        used_edits: list[ConceptEditKey] = []
        used_edit_keys: set[ConceptEditKey] = set()
        foil_text = choices[foil]
        rounds = 0
        repair_calls = 0

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
                used_edits=list(used_edits),
            )
            proposals = _prioritise_concept_diversity(proposals, used_edits)
            proposals = proposals[:remaining_budget]

            for proposed_edit in proposals:
                if len(attempts) >= budget:
                    break

                description = describe_concept_edit(proposed_edit)
                key = concept_edit_key(proposed_edit)
                if key in used_edit_keys:
                    _record_rejection(
                        proposer,
                        recent_rejects,
                        description,
                        "empty_or_duplicate",
                    )
                    continue
                used_edit_keys.add(key)
                used_edits.append(key)

                applied = apply_concept_edit(scenario, proposed_edit)
                if applied is None:
                    _record_rejection(
                        proposer,
                        recent_rejects,
                        description,
                        "invalid_span",
                    )
                    if repair_calls >= MAX_REPAIR_CALLS:
                        continue
                    repair_calls += 1
                    repaired = proposer.repair_concept_edit(
                        scenario,
                        choices,
                        foil,
                        proposed_edit,
                        allowed_concepts=CONCEPT_CLASSES,
                        used_edits=list(used_edits),
                    )
                    repaired_edit = _grounding_only_repair(proposed_edit, repaired)
                    if repaired_edit is None:
                        if repaired is not None:
                            _record_rejection(
                                proposer,
                                recent_rejects,
                                describe_concept_edit(repaired),
                                "constraint_violation",
                            )
                        continue

                    repaired_description = describe_concept_edit(repaired_edit)
                    repaired_key = concept_edit_key(repaired_edit)
                    if repaired_key in used_edit_keys:
                        _record_rejection(
                            proposer,
                            recent_rejects,
                            repaired_description,
                            "empty_or_duplicate",
                        )
                        continue
                    used_edit_keys.add(repaired_key)
                    used_edits.append(repaired_key)
                    applied = apply_concept_edit(scenario, repaired_edit)
                    if applied is None:
                        _record_rejection(
                            proposer,
                            recent_rejects,
                            repaired_description,
                            "invalid_span",
                        )
                        continue

                modified_scenario, resolved_edit = applied
                description = describe_concept_edit(resolved_edit)
                key = normalise_key(modified_scenario)
                if not key or key in seen:
                    _record_rejection(
                        proposer,
                        recent_rejects,
                        description,
                        "empty_or_duplicate",
                    )
                    continue

                seen.add(key)
                if is_degenerate_foil_leak(scenario, modified_scenario, foil_text):
                    _record_rejection(
                        proposer,
                        recent_rejects,
                        description,
                        "foil_leak",
                    )
                    continue

                if exceeds_changed_fraction(
                    scenario,
                    modified_scenario,
                    self._max_changed_fraction,
                ):
                    _record_rejection(
                        proposer,
                        recent_rejects,
                        description,
                        "changed_fraction",
                    )
                    continue

                record_candidate_outcome(proposer, "unique_valid")
                prediction = model.target_predict(modified_scenario, choices)
                record_candidate_outcome(proposer, "target_verified")
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


def _grounding_only_repair(
    original: ConceptEdit,
    repaired: ConceptEdit | None,
) -> ConceptEdit | None:
    if repaired is None:
        return None
    if repaired.concept_class != original.concept_class:
        return None
    if normalise_concept_text(repaired.replacement_span) != normalise_concept_text(
        original.replacement_span
    ):
        return None
    return replace(original, original_span=repaired.original_span)


def _prioritise_concept_diversity(
    proposals: list[ConceptEdit],
    used_edits: list[ConceptEditKey],
) -> list[ConceptEdit]:
    used_classes = {concept_class for concept_class, _, _ in used_edits}
    used_spans = {(concept_class, span) for concept_class, span, _ in used_edits}
    remaining = list(enumerate(proposals))
    ordered: list[ConceptEdit] = []

    while remaining:
        position, (_, selected) = min(
            enumerate(remaining),
            key=lambda item: (
                item[1][1].concept_class in used_classes,
                concept_span_key(item[1][1]) in used_spans,
                item[1][0],
            ),
        )
        remaining.pop(position)
        ordered.append(selected)
        used_classes.add(selected.concept_class)
        used_spans.add(concept_span_key(selected))
    return ordered


def _record_rejection(
    proposer: Proposer,
    recent_rejects: list[str],
    description: str,
    outcome: CandidateOutcome,
) -> None:
    recent_rejects.append(description)
    record_candidate_outcome(proposer, outcome)
