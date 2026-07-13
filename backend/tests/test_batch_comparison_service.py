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
