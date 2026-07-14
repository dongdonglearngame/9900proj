from types import SimpleNamespace

from app.harness.target_predict import PredictionResult
from app.repositories.factory import (
    get_counterfactual_repository,
    get_metrics_repository,
)
from app.schemas.comparison import ComparisonCreateRequest
from app.schemas.scenario import ScenarioItem, ScenariosResponse
from app.services.batch_comparison_service import BatchComparisonService

CHOICES = {
    "A": "Ignore the texts and continue sleeping",
    "B": "Tell her friend to seek professional help",
    "C": "Stay up and lend a listening ear",
    "D": "Suggest her friend find a new partner",
}

REGINA = ScenarioItem(
    question_id="q_regina_001",
    scenario_item_id="s_regina_001",
    task_type="EU",
    dimension="emotion_cause",
    subject="Regina",
    scenario=(
        "Regina's best friend recently broke up with her longtime partner and is "
        "texting Regina in the middle of the night expressing feelings of loneliness."
    ),
    question_text="What should Regina do?",
    choices=CHOICES,
    label="C",
)


class StubScenarioSource:
    def __init__(self, items: list[ScenarioItem] | None = None) -> None:
        self._items = items or [REGINA]

    def list_scenarios(
        self,
        task_type: str | None,
        dimension: str | None,
        limit: int,
        offset: int,
    ) -> ScenariosResponse:
        _ = task_type, dimension
        items = self._items[offset : offset + limit]
        return ScenariosResponse(items=items, total=len(self._items))


class StubExperimentRunRepository:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(id=f"run_{len(self.calls)}")


class NoAnswerPredictionService:
    def target_predict(
        self,
        scenario: str,
        choices: dict[str, str],
        model: str,
    ) -> PredictionResult:
        _ = scenario
        return PredictionResult(
            status="parse_failed",
            answer=None,
            answer_text=None,
            model=model,
            prompt_template_version="test",
            cache_hit=False,
            raw_response="",
            option_logprobs={letter: None for letter in choices},
            option_probs={letter: None for letter in choices},
            top_logprobs_raw=[],
            runtime_seconds=0.1,
        )


def make_request(**overrides) -> ComparisonCreateRequest:
    defaults = {
        "model": "mock",
        "strategy_ids": ["s1_word_greedy"],
        "selected_scenario": REGINA,
        "selected_question_id": REGINA.question_id,
        "task_type": "EU",
        "limit": 1,
        "budget": 5,
        "foil_mode": "single",
    }
    return ComparisonCreateRequest(**{**defaults, **overrides})


def test_single_foil_uses_ground_truth_when_original_prediction_differs() -> None:
    service = BatchComparisonService(scenario_source=StubScenarioSource())

    result = service.run_comparison(make_request())

    assert result.selected_scenario.original_answer == "A"
    assert result.selected_scenario.foils == ["C"]
    assert len(result.rows) == 1
    assert result.rows[0].original_answer == "A"
    assert result.rows[0].foil == "C"
    assert result.rows[0].strategy_id == "s1_word_greedy"
    assert result.summary[0].runs == 1
    assert result.rows[0].experiment_run_id == result.experiment_run_id
    assert result.rows[0].result.experiment_run_id == result.experiment_run_id


def test_single_foil_uses_nearest_non_original_when_prediction_matches_label() -> None:
    already_correct = REGINA.model_copy(
        update={
            "question_id": "q_regina_evening",
            "scenario": REGINA.scenario.replace("middle of the night", "early evening"),
            "label": "C",
        }
    )
    service = BatchComparisonService(scenario_source=StubScenarioSource([already_correct]))

    result = service.run_comparison(
        make_request(
            selected_scenario=already_correct,
            selected_question_id=already_correct.question_id,
        )
    )

    assert result.selected_scenario.original_answer == "C"
    assert result.selected_scenario.foils == ["A"]


def test_all_non_original_foil_mode_runs_each_possible_foil() -> None:
    service = BatchComparisonService(scenario_source=StubScenarioSource())

    result = service.run_comparison(make_request(foil_mode="all_non_original"))

    assert [row.foil for row in result.rows] == ["B", "C", "D"]
    assert result.summary[0].runs == 3
    assert result.summary[0].skipped_count == 0


def test_selected_scenario_is_included_even_when_not_in_batch_window() -> None:
    service = BatchComparisonService(scenario_source=StubScenarioSource())

    result = service.run_comparison(make_request(offset=1))

    assert result.selected_scenario.scenario.question_id == REGINA.question_id
    assert result.rows[0].question_id == REGINA.question_id


def test_job_creates_experiment_run_and_persists_synchronous_results() -> None:
    experiment_runs = StubExperimentRunRepository()
    results_repo = get_counterfactual_repository()
    metrics_repo = get_metrics_repository()
    result_count = len(results_repo.list_results())
    metric_count = len(metrics_repo.list_metrics())
    service = BatchComparisonService(
        scenario_source=StubScenarioSource(),
        experiment_run_repository=experiment_runs,
    )
    request = make_request()

    created = service.create_job(request)
    service.run_job(created.job_id, request)
    job = service.get_job(created.job_id)

    assert created.experiment_run_id == "run_1"
    assert experiment_runs.calls[0]["strategy_ids"] == ["s1_word_greedy"]
    assert experiment_runs.calls[0]["prompt_template_version"]
    assert job is not None
    assert job.status == "completed"
    assert job.experiment_run_id == created.experiment_run_id
    assert job.result.experiment_run_id == created.experiment_run_id
    assert service.get_job_by_run(created.experiment_run_id) == job
    assert len(results_repo.list_results()) == result_count + 1
    assert len(metrics_repo.list_metrics()) == metric_count + 1
    assert results_repo.list_results()[-1].experiment_run_id == created.experiment_run_id
    assert metrics_repo.list_metrics()[-1].experiment_run_id == created.experiment_run_id


def test_missing_question_ids_are_reported_as_partial_coverage() -> None:
    service = BatchComparisonService(scenario_source=StubScenarioSource())

    result = service.run_comparison(
        make_request(
            selected_scenario=None,
            selected_question_id=None,
            question_ids=[REGINA.question_id, "q_missing"],
            limit=2,
        )
    )

    assert result.coverage.requested_scenarios == 2
    assert result.coverage.resolved_scenarios == 1
    assert result.coverage.missing_question_ids == ["q_missing"]
    assert result.coverage.scenario_coverage_rate == 0.5
    assert result.coverage.partial_coverage is True


def test_all_missing_question_ids_return_an_empty_partial_result() -> None:
    service = BatchComparisonService(scenario_source=StubScenarioSource())

    result = service.run_comparison(
        make_request(
            selected_scenario=None,
            selected_question_id=None,
            question_ids=["q_missing"],
        )
    )

    assert result.rows == []
    assert result.coverage.resolved_scenarios == 0
    assert result.coverage.missing_question_ids == ["q_missing"]
    assert result.coverage.scenario_coverage_rate == 0.0
    assert result.coverage.partial_coverage is True
    assert result.summary[0].runs == 0
    assert result.summary[0].partial_coverage is True


def test_skipped_cases_remain_in_flip_rate_denominator() -> None:
    service = BatchComparisonService(
        scenario_source=StubScenarioSource(),
        prediction_service=NoAnswerPredictionService(),
    )

    result = service.run_comparison(make_request())
    summary = result.summary[0]

    assert summary.runs == 1
    assert summary.attempted_count == 0
    assert summary.skipped_count == 1
    assert summary.flip_rate == 0.0
    assert summary.coverage_rate == 0.0
    assert summary.partial_coverage is True
    assert result.coverage.execution_coverage_rate == 0.0
    assert result.coverage.partial_coverage is True
