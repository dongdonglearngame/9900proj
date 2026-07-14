from app.metrics.diff import word_diff
from app.metrics.edit_distance import changed_word_fraction, token_edit_distance
from app.metrics.scorer import compute_counterfactual_metrics


def test_word_diff_for_regina_edit() -> None:
    original = "Regina is texting in the middle of the night."
    modified = "Regina is texting in the early evening."
    spans = word_diff(original, modified)
    assert spans[0].type == "replace"
    assert spans[0].original == "middle of the night."
    assert spans[0].modified == "early evening."


def test_token_edit_distance() -> None:
    assert token_edit_distance("a b c", "a x c") == 1
    assert changed_word_fraction("a b c", "a x c") == 0.3333


def test_foil_logprob_metrics_exclude_missing_scores_and_report_coverage() -> None:
    metrics = compute_counterfactual_metrics(
        original="original",
        modified=None,
        flip_success=False,
        search_calls=3,
        postprocess_calls=0,
        proposer_calls=1,
        runtime_seconds=1.0,
        original_foil_logprob=-2.0,
        candidate_foil_logprobs=[-1.0, None, -3.0],
        selected_foil_logprob=None,
    )

    assert metrics.foil_logprob_delta is None
    assert metrics.mean_foil_logprob_delta == 0.0
    assert metrics.max_foil_logprob_delta == 1.0
    assert metrics.positive_delta_rate == 0.5
    assert metrics.logprob_coverage == 0.666667


def test_foil_logprob_metrics_report_zero_coverage_when_baseline_is_missing() -> None:
    metrics = compute_counterfactual_metrics(
        original="original",
        modified=None,
        flip_success=False,
        search_calls=1,
        postprocess_calls=0,
        proposer_calls=1,
        runtime_seconds=1.0,
        original_foil_logprob=None,
        candidate_foil_logprobs=[-1.0],
    )

    assert metrics.mean_foil_logprob_delta is None
    assert metrics.positive_delta_rate is None
    assert metrics.logprob_coverage == 0.0
