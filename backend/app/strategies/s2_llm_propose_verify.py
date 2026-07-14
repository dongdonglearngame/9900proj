import re
from dataclasses import replace

from app.core.config import get_settings
from app.metrics.diff import word_diff
from app.metrics.edit_distance import changed_word_fraction
from app.proposer.harness import record_candidate_outcome
from app.strategies._candidate_filters import (
    exceeds_changed_fraction,
    is_degenerate_foil_leak,
    normalise_key,
)
from app.strategies.base import (
    AttemptRecord,
    CounterfactualResult,
    CounterfactualStrategy,
    ProposedEdit,
    Proposer,
    TargetModel,
)

AVOID_WINDOW = 8
FEEDBACK_TEXT_LIMIT = 240
WORD_RE = re.compile(r"[A-Za-z0-9']+")


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
            else settings.s2_proposer_candidates_per_round
        )
        self._max_rounds = (
            max_rounds if max_rounds is not None else settings.s2_proposer_max_rounds
        )
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
        recent_feedback: list[str] = []
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
                avoid=recent_feedback[-AVOID_WINDOW:],
            )[:remaining_budget]

            valid_proposals: list[ProposedEdit] = []
            for edit in proposals:
                modified_scenario = edit.modified_scenario.strip()
                key = normalise_key(modified_scenario)
                if not key or key in seen:
                    record_candidate_outcome(proposer, "empty_or_duplicate")
                    recent_feedback.append(
                        _feedback("empty_or_duplicate", modified_scenario or "<empty>")
                    )
                    continue

                if is_degenerate_foil_leak(scenario, modified_scenario, foil_text):
                    seen.add(key)
                    record_candidate_outcome(proposer, "foil_leak")
                    recent_feedback.append(_feedback("foil_leak", modified_scenario))
                    continue

                if exceeds_changed_fraction(
                    scenario,
                    modified_scenario,
                    self._max_changed_fraction,
                ):
                    seen.add(key)
                    record_candidate_outcome(proposer, "changed_fraction")
                    recent_feedback.append(_feedback("changed_fraction", modified_scenario))
                    continue

                seen.add(key)
                record_candidate_outcome(proposer, "unique_valid")
                valid_proposals.append(replace(edit, modified_scenario=modified_scenario))

            for edit in _rank_proposals(scenario, valid_proposals):
                if len(attempts) >= budget:
                    break

                modified_scenario = edit.modified_scenario
                prediction = model.target_predict(modified_scenario, choices)
                record_candidate_outcome(proposer, "target_verified")
                success = prediction.answer == foil
                attempts.append(
                    AttemptRecord(
                        modified_scenario=modified_scenario,
                        prediction=prediction,
                        success=success,
                        edit_description=_edit_description(edit),
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

                predicted = prediction.answer or prediction.status
                recent_feedback.append(
                    _feedback(f"target_answer={predicted}", modified_scenario)
                )

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


def _rank_proposals(original: str, proposals: list[ProposedEdit]) -> list[ProposedEdit]:
    """Prefer minimal candidates, using edit diversity as a deterministic tie-breaker."""

    if len(proposals) < 2:
        return proposals

    change_tokens = [_changed_tokens(original, edit.modified_scenario) for edit in proposals]
    diversity_scores: list[float] = []
    for index, tokens in enumerate(change_tokens):
        distances = [
            _jaccard_distance(tokens, other_tokens)
            for other_index, other_tokens in enumerate(change_tokens)
            if other_index != index
        ]
        diversity_scores.append(sum(distances) / len(distances) if distances else 0.0)

    indexed = list(enumerate(proposals))
    indexed.sort(
        key=lambda item: (
            changed_word_fraction(original, item[1].modified_scenario) or 0.0,
            -diversity_scores[item[0]],
            item[0],
        )
    )
    return [edit for _, edit in indexed]


def _changed_tokens(original: str, modified: str) -> set[str]:
    text = " ".join(
        f"{span.original} {span.modified}"
        for span in word_diff(original, modified)
    )
    return {token.casefold() for token in WORD_RE.findall(text)}


def _jaccard_distance(left: set[str], right: set[str]) -> float:
    union = left | right
    if not union:
        return 0.0
    return 1.0 - (len(left & right) / len(union))


def _feedback(reason: str, scenario: str) -> str:
    compact = re.sub(r"\s+", " ", scenario).strip()
    if len(compact) > FEEDBACK_TEXT_LIMIT:
        compact = f"{compact[: FEEDBACK_TEXT_LIMIT - 3]}..."
    return f"{reason}: {compact}"


def _edit_description(edit: ProposedEdit) -> str | None:
    details: list[str] = []
    if edit.change_type:
        details.append(f"change_type={edit.change_type}")
    if edit.changed_span:
        details.append(f"changed_span={edit.changed_span}")
    if edit.rationale:
        details.append(edit.rationale)
    return "; ".join(details) or None
