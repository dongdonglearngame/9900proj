import logging
import re
from dataclasses import dataclass
from typing import Literal

from app.core.config import get_settings
from app.harness.target_predict import PredictionResult
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
    Proposer,
    TargetModel,
)

WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
MASK_TOKEN = "[MASK]"
AVOID_WINDOW = 8
DEFAULT_MAX_IMPORTANCE_CANDIDATES = 32
LOGPROB_DELTA_MODE = "foil_logprob_delta"
ANSWER_CHANGE_FALLBACK_MODE = "answer_change_fallback"

logger = logging.getLogger(__name__)

ImportanceScoringMode = Literal[
    "foil_logprob_delta",
    "answer_change_fallback",
]

STOPWORDS = {
    "a",
    "about",
    "after",
    "all",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "but",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "hers",
    "him",
    "his",
    "i",
    "in",
    "is",
    "it",
    "its",
    "my",
    "of",
    "on",
    "or",
    "our",
    "she",
    "that",
    "the",
    "their",
    "them",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "with",
    "you",
    "your",
}


@dataclass(frozen=True)
class TokenCandidate:
    text: str
    start: int
    end: int
    index: int


@dataclass(frozen=True)
class ImportanceRecord:
    token: TokenCandidate
    score: float
    scoring_mode: ImportanceScoringMode
    prediction: PredictionResult


@dataclass(frozen=True)
class ImportanceScore:
    value: float
    mode: ImportanceScoringMode


@dataclass(frozen=True)
class MaskedSpan:
    start: int
    end: int
    text: str
    score: float
    token_count: int


class S4ImportanceInfillingStrategy(CounterfactualStrategy):
    """S4: black-box occlusion importance ranking plus constrained infilling."""

    id = "s4_importance_infilling"
    name = "S4 Importance-guided Infilling"

    def __init__(
        self,
        *,
        candidates_per_round: int | None = None,
        max_changed_fraction: float | None = None,
        max_importance_candidates: int | None = None,
    ) -> None:
        settings = get_settings()
        self._candidates_per_round = (
            candidates_per_round
            if candidates_per_round is not None
            else settings.proposer_candidates_per_round
        )
        self._max_changed_fraction = (
            max_changed_fraction
            if max_changed_fraction is not None
            else settings.proposer_max_changed_fraction
        )
        self._max_importance_candidates = (
            max_importance_candidates
            if max_importance_candidates is not None
            else DEFAULT_MAX_IMPORTANCE_CANDIDATES
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
        if budget <= 0:
            return self._not_found(scenario, foil, attempts, "S4 budget exhausted")

        target_calls = 0

        def target_predict(candidate_scenario: str) -> PredictionResult:
            nonlocal target_calls
            target_calls += 1
            return model.target_predict(candidate_scenario, choices)

        baseline = target_predict(scenario)
        importance_budget = _importance_scoring_budget(budget)
        ranked = self._rank_tokens(
            scenario=scenario,
            choices=choices,
            model_predict=target_predict,
            baseline=baseline,
            foil=foil,
            budget_remaining=importance_budget,
        )
        if not ranked:
            return self._not_found(
                scenario,
                foil,
                attempts,
                "no S4 importance candidates could be scored within budget",
            )

        seen = {normalise_key(scenario)}
        recent_rejects: list[str] = []
        foil_text = choices[foil]

        for mask_count in range(1, len(ranked) + 1):
            if target_calls >= budget:
                break

            selected = ranked[:mask_count]
            spans = _merge_ranked_tokens(scenario, selected)
            masked_scenario = _mask_spans(scenario, spans)
            if MASK_TOKEN not in masked_scenario:
                continue

            proposals = proposer.infill(
                scenario,
                masked_scenario,
                choices,
                foil,
                count=self._candidates_per_round,
                avoid=recent_rejects[-AVOID_WINDOW:],
            )
            for edit in proposals:
                if target_calls >= budget:
                    break

                modified_scenario = edit.modified_scenario.strip()
                key = normalise_key(modified_scenario)
                if not key or key in seen:
                    record_candidate_outcome(proposer, "empty_or_duplicate")
                    continue

                seen.add(key)
                if MASK_TOKEN in modified_scenario:
                    record_candidate_outcome(proposer, "constraint_violation")
                    recent_rejects.append(modified_scenario)
                    continue

                if not _preserves_unmasked_text(masked_scenario, modified_scenario):
                    record_candidate_outcome(proposer, "constraint_violation")
                    recent_rejects.append(modified_scenario)
                    continue

                if is_degenerate_foil_leak(scenario, modified_scenario, foil_text):
                    record_candidate_outcome(proposer, "foil_leak")
                    recent_rejects.append(modified_scenario)
                    continue

                if exceeds_changed_fraction(
                    scenario,
                    modified_scenario,
                    self._max_changed_fraction,
                ):
                    record_candidate_outcome(proposer, "changed_fraction")
                    recent_rejects.append(modified_scenario)
                    continue

                record_candidate_outcome(proposer, "unique_valid")
                prediction = target_predict(modified_scenario)
                record_candidate_outcome(proposer, "target_verified")
                success = prediction.answer == foil
                attempts.append(
                    AttemptRecord(
                        modified_scenario=modified_scenario,
                        prediction=prediction,
                        success=success,
                        edit_description=_edit_description(
                            spans=spans,
                            scoring_modes={record.scoring_mode for record in selected},
                            mask_count=mask_count,
                            total_ranked=len(ranked),
                            rationale=edit.rationale,
                        ),
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

        return self._not_found(
            scenario,
            foil,
            attempts,
            "no S4 infilled candidate flipped the scenario within budget",
        )

    def _rank_tokens(
        self,
        *,
        scenario: str,
        choices: dict[str, str],
        model_predict,
        baseline: PredictionResult,
        foil: str,
        budget_remaining: int,
    ) -> list[ImportanceRecord]:
        _ = choices
        if budget_remaining <= 0:
            return []

        tokens = _candidate_tokens(scenario)[: self._max_importance_candidates]
        records: list[ImportanceRecord] = []
        for token in tokens[:budget_remaining]:
            occluded = _delete_span(scenario, token.start, token.end)
            if not occluded or normalise_key(occluded) == normalise_key(scenario):
                continue

            prediction = model_predict(occluded)
            importance = _importance_score(baseline, prediction, foil)
            records.append(
                ImportanceRecord(
                    token=token,
                    score=importance.value,
                    scoring_mode=importance.mode,
                    prediction=prediction,
                )
            )

        if any(record.scoring_mode == ANSWER_CHANGE_FALLBACK_MODE for record in records):
            logger.warning(
                "S4 importance scoring is using answer-change fallback for candidates "
                "without foil logprobs"
            )

        return sorted(records, key=_importance_sort_key)

    def _not_found(
        self,
        scenario: str,
        foil: str,
        attempts: list[AttemptRecord],
        message: str,
    ) -> CounterfactualResult:
        return CounterfactualResult(
            status="not_found",
            original_scenario=scenario,
            modified_scenario=None,
            new_answer=None,
            foil=foil,
            strategy_id=self.id,
            attempts=attempts,
            message=message,
        )


def _candidate_tokens(scenario: str) -> list[TokenCandidate]:
    tokens: list[TokenCandidate] = []
    for index, match in enumerate(WORD_RE.finditer(scenario)):
        text = match.group(0)
        if _is_content_token(text):
            tokens.append(
                TokenCandidate(
                    text=text,
                    start=match.start(),
                    end=match.end(),
                    index=index,
                )
            )
    return tokens


def _is_content_token(token: str) -> bool:
    lower = token.casefold()
    return len(lower) > 2 and lower not in STOPWORDS


def _delete_span(scenario: str, start: int, end: int) -> str:
    prefix = scenario[:start].rstrip()
    suffix = scenario[end:].lstrip()
    if not prefix:
        return suffix
    if not suffix:
        return prefix
    if suffix[:1] in {".", ",", ";", ":", "?", "!"}:
        return f"{prefix}{suffix}"
    return f"{prefix} {suffix}"


def _importance_score(
    baseline: PredictionResult,
    occluded: PredictionResult,
    foil: str,
) -> ImportanceScore:
    baseline_foil = (baseline.option_logprobs or {}).get(foil)
    occluded_foil = (occluded.option_logprobs or {}).get(foil)
    if baseline_foil is not None and occluded_foil is not None:
        return ImportanceScore(
            value=occluded_foil - baseline_foil,
            mode=LOGPROB_DELTA_MODE,
        )

    if occluded.answer == foil and baseline.answer != foil:
        fallback_score = 2.0
    elif occluded.answer != baseline.answer:
        fallback_score = 1.0
    else:
        fallback_score = 0.0
    return ImportanceScore(
        value=fallback_score,
        mode=ANSWER_CHANGE_FALLBACK_MODE,
    )


def _importance_sort_key(record: ImportanceRecord) -> tuple[int, float, int]:
    mode_priority = 0 if record.scoring_mode == LOGPROB_DELTA_MODE else 1
    return (mode_priority, -record.score, record.token.start)


def _importance_scoring_budget(total_budget: int) -> int:
    if total_budget <= 0:
        return 0
    verification_reserve = max(1, total_budget // 3)
    return max(0, total_budget - 1 - verification_reserve)


def _merge_ranked_tokens(
    scenario: str,
    records: list[ImportanceRecord],
) -> list[MaskedSpan]:
    spans: list[MaskedSpan] = []
    for record in sorted(records, key=lambda item: item.token.start):
        token = record.token
        if spans and _gap_is_mergeable(scenario[spans[-1].end : token.start]):
            previous = spans[-1]
            spans[-1] = MaskedSpan(
                start=previous.start,
                end=token.end,
                text=scenario[previous.start : token.end],
                score=previous.score + record.score,
                token_count=previous.token_count + 1,
            )
        else:
            spans.append(
                MaskedSpan(
                    start=token.start,
                    end=token.end,
                    text=scenario[token.start : token.end],
                    score=record.score,
                    token_count=1,
                )
            )
    return spans


def _gap_is_mergeable(gap: str) -> bool:
    return all(not _is_content_token(match.group(0)) for match in WORD_RE.finditer(gap))


def _mask_spans(scenario: str, spans: list[MaskedSpan]) -> str:
    result = scenario
    for span in sorted(spans, key=lambda item: item.start, reverse=True):
        result = f"{result[: span.start]}{MASK_TOKEN}{result[span.end :]}"
    return result


def _preserves_unmasked_text(masked_scenario: str, modified_scenario: str) -> bool:
    pieces = masked_scenario.split(MASK_TOKEN)
    if len(pieces) == 1:
        return masked_scenario == modified_scenario

    pattern = "^" + "(.*?)".join(re.escape(piece) for piece in pieces) + "$"
    match = re.fullmatch(pattern, modified_scenario, flags=re.DOTALL)
    if match is None:
        return False
    return all(group.strip() for group in match.groups())


def _edit_description(
    *,
    spans: list[MaskedSpan],
    scoring_modes: set[ImportanceScoringMode],
    mask_count: int,
    total_ranked: int,
    rationale: str | None,
) -> str:
    masked_text = " | ".join(f"'{span.text}'" for span in spans)
    importance_score = sum(span.score for span in spans)
    scoring_mode = "+".join(sorted(scoring_modes))
    proportion = mask_count / max(1, total_ranked)
    description = (
        f"mask_count={mask_count}; mask_proportion={proportion:.4f}; "
        f"importance_score={importance_score:.4f}; scoring_mode={scoring_mode}; "
        f"masked_spans={masked_text}"
    )
    if rationale:
        description = f"{description}; rationale={rationale}"
    return description
