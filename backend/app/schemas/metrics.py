from app.schemas.common import APIModel


class CounterfactualMetrics(APIModel):
    experiment_run_id: str | None = None
    flip_success: bool
    token_edit_distance: int | None
    changed_word_fraction: float | None
    perplexity: float | None = None
    fluency_score: float | None = None
    search_calls: int
    postprocess_calls: int
    proposer_calls: int
    total_target_calls: int
    runtime_seconds: float
    foil_logprob_delta: float | None = None
    mean_foil_logprob_delta: float | None = None
    max_foil_logprob_delta: float | None = None
    positive_delta_rate: float | None = None
    logprob_coverage: float | None = None
