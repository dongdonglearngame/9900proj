from app.metrics.edit_distance import changed_word_fraction, token_edit_distance
from app.schemas.metrics import CounterfactualMetrics


def compute_counterfactual_metrics(
    *,
    original: str,
    modified: str | None,
    flip_success: bool,
    search_calls: int,
    postprocess_calls: int,
    proposer_calls: int,
    runtime_seconds: float,
    original_foil_logprob: float | None = None,
    candidate_foil_logprobs: list[float | None] | None = None,
    selected_foil_logprob: float | None = None,
) -> CounterfactualMetrics:
    total_target_calls = search_calls + postprocess_calls
    candidate_scores = candidate_foil_logprobs or []
    covered_deltas = (
        [score - original_foil_logprob for score in candidate_scores if score is not None]
        if original_foil_logprob is not None
        else []
    )
    selected_delta = (
        selected_foil_logprob - original_foil_logprob
        if selected_foil_logprob is not None and original_foil_logprob is not None
        else None
    )
    logprob_coverage = (
        len(covered_deltas) / len(candidate_scores) if candidate_scores else None
    )
    positive_delta_rate = (
        len([delta for delta in covered_deltas if delta > 0]) / len(covered_deltas)
        if covered_deltas
        else None
    )
    return CounterfactualMetrics(
        flip_success=flip_success,
        token_edit_distance=token_edit_distance(original, modified) if flip_success else None,
        changed_word_fraction=changed_word_fraction(original, modified) if flip_success else None,
        perplexity=None,
        fluency_score=None,
        search_calls=search_calls,
        postprocess_calls=postprocess_calls,
        proposer_calls=proposer_calls,
        total_target_calls=total_target_calls,
        runtime_seconds=runtime_seconds,
        foil_logprob_delta=_rounded(selected_delta),
        mean_foil_logprob_delta=_rounded(
            sum(covered_deltas) / len(covered_deltas) if covered_deltas else None
        ),
        max_foil_logprob_delta=_rounded(max(covered_deltas) if covered_deltas else None),
        positive_delta_rate=_rounded(positive_delta_rate),
        logprob_coverage=_rounded(logprob_coverage),
    )


def _rounded(value: float | None) -> float | None:
    return round(value, 6) if value is not None else None
