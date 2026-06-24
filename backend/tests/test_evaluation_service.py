from app.harness.target_predict import PredictionResult
from app.schemas.scenario import ScenarioItem, ScenariosResponse
from app.services.evaluation_service import EvaluationService


class FakeScenarioSource:
    def __init__(self) -> None:
        self.calls: list[tuple[str | None, str | None, int, int]] = []
        self.items = [
            ScenarioItem(
                question_id="q_1",
                scenario_item_id="s_1",
                task_type="EA",
                dimension="action",
                subject="Regina",
                scenario="first scenario",
                question_text="What should Regina do?",
                choices={"A": "wrong", "B": "also wrong", "C": "right", "D": "other"},
                label="C",
            ),
            ScenarioItem(
                question_id="q_2",
                scenario_item_id="s_2",
                task_type="EA",
                dimension="response",
                subject="Omar",
                scenario="second scenario",
                question_text="What should Omar say?",
                choices={"A": "right", "B": "wrong", "C": "also wrong", "D": "other"},
                label="A",
            ),
        ]

    def list_scenarios(
        self,
        task_type: str | None,
        dimension: str | None,
        limit: int,
        offset: int,
    ) -> ScenariosResponse:
        self.calls.append((task_type, dimension, limit, offset))
        filtered = [item for item in self.items if item.task_type == task_type]
        return ScenariosResponse(items=filtered[offset : offset + limit], total=len(filtered))


class EmptyScenarioSource:
    def list_scenarios(
        self,
        task_type: str | None,
        dimension: str | None,
        limit: int,
        offset: int,
    ) -> ScenariosResponse:
        return ScenariosResponse(items=[], total=0)


class FakePredictor:
    def target_predict(
        self,
        scenario: str,
        choices: dict[str, str],
        model: str,
    ) -> PredictionResult:
        answer = "C" if scenario == "first scenario" else "B"
        return PredictionResult(
            status="ok",
            answer=answer,
            answer_text=choices[answer],
            model=model,
            prompt_template_version="test",
            cache_hit=scenario == "second scenario",
            raw_response=answer,
            option_logprobs={"A": None, "B": None, "C": None, "D": None},
            option_probs={"A": None, "B": None, "C": None, "D": None},
            top_logprobs_raw=[],
            runtime_seconds=0.0,
        )


def test_run_baseline_measures_accuracy_by_dimension() -> None:
    source = FakeScenarioSource()
    service = EvaluationService(
        scenario_source=source,
        predictor=FakePredictor(),
        page_size=1,
    )

    result = service.run_baseline(model="mock", task_type="EA")

    assert result["status"] == "ok"
    assert result["total"] == 2
    assert result["correct"] == 1
    assert result["accuracy"] == 0.5
    assert result["cache_hits"] == 1
    assert result["by_dimension"]["action"]["accuracy"] == 1.0
    assert result["by_dimension"]["response"]["accuracy"] == 0.0
    assert source.calls == [
        ("EA", None, 1, 0),
        ("EA", None, 1, 1),
    ]


def test_run_baseline_handles_empty_task() -> None:
    service = EvaluationService(
        scenario_source=EmptyScenarioSource(),
        predictor=FakePredictor(),
    )

    result = service.run_baseline(model="mock", task_type="EU")

    assert result["status"] == "no_questions"
    assert result["total"] == 0
    assert result["accuracy"] is None
