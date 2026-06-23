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
) -> CounterfactualMetrics:
    total_target_calls = search_calls + postprocess_calls
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
    )
