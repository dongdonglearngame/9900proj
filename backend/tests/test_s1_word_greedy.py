from dataclasses import replace

from fastapi.testclient import TestClient

from app.llm.mock_client import MockLLMClient
from app.main import app
from app.strategies.base import FrozenTargetModel
from app.strategies.s1_word_greedy import S1WordGreedyStrategy

CHOICES = {
    "A": "Ignore the texts and continue sleeping",
    "B": "Tell her friend to seek professional help",
    "C": "Stay up and lend a listening ear",
    "D": "Suggest her friend find a new partner",
}


def _target_model_flips_when(condition):
    def target_predict(scenario: str, choices: dict[str, str], model: str):
        prediction = MockLLMClient().predict(scenario=scenario, choices=choices, model=model)
        if not condition(scenario):
            return prediction
        return replace(
            prediction,
            answer="C",
            answer_text=choices["C"],
            raw_response="C",
        )

    return FrozenTargetModel(model_id="mock", target_predict_fn=target_predict)


def test_s1_finds_regina_demo_edit() -> None:
    scenario = (
        "Regina's best friend recently broke up with her longtime partner and is "
        "texting Regina in the middle of the night expressing feelings of loneliness."
    )
    model = FrozenTargetModel(model_id="mock", target_predict_fn=MockLLMClient().predict)

    result = S1WordGreedyStrategy().generate(
        scenario=scenario,
        choices=CHOICES,
        model=model,
        foil="C",
        budget=20,
    )

    assert result.status == "success"
    assert result.new_answer == "C"
    assert result.modified_scenario is not None
    assert "early evening" in result.modified_scenario
    assert len(result.attempts) == 1
    assert result.attempts[0].success


def test_s1_respects_zero_budget() -> None:
    scenario = (
        "Regina's best friend recently broke up with her longtime partner and is "
        "texting Regina in the middle of the night expressing feelings of loneliness."
    )

    def fail_if_called(scenario: str, choices: dict[str, str], model: str):
        raise AssertionError("target_predict should not be called when budget is zero")

    model = FrozenTargetModel(model_id="mock", target_predict_fn=fail_if_called)
    result = S1WordGreedyStrategy().generate(
        scenario=scenario,
        choices=CHOICES,
        model=model,
        foil="C",
        budget=0,
    )

    assert result.status == "not_found"
    assert result.attempts == []


def test_counterfactual_api_runs_s1_strategy() -> None:
    client = TestClient(app)
    scenario = (
        "Regina's best friend recently broke up with her longtime partner and is "
        "texting Regina late at night expressing feelings of loneliness."
    )

    created = client.post(
        "/counterfactual",
        json={
            "question_id": "q_regina_late_night",
            "scenario": scenario,
            "choices": CHOICES,
            "model": "mock",
            "original_answer": "A",
            "foil": "C",
            "strategy_id": "s1_word_greedy",
            "budget": 20,
        },
    ).json()
    job = client.get(f"/counterfactual/jobs/{created['job_id']}").json()

    assert job["status"] == "completed"
    assert job["result"]["status"] == "success"
    assert job["result"]["new_answer"] == "C"
    assert "early evening" in job["result"]["modified_scenario"]
    assert job["result"]["metrics"]["search_calls"] == 1


def test_s1_uses_systematic_emotion_replacement_beyond_demo_seed() -> None:
    scenario = "Maya feels panicked after a classmate ignores her message."
    model = _target_model_flips_when(
        lambda candidate: "worried" in candidate.lower() or "calm" in candidate.lower()
    )

    result = S1WordGreedyStrategy().generate(
        scenario=scenario,
        choices=CHOICES,
        model=model,
        foil="C",
        budget=10,
    )

    assert result.status == "success"
    assert result.modified_scenario is not None
    assert "panicked" not in result.modified_scenario.lower()
    assert result.attempts[0].edit_description == "replace 'panicked' with 'worried'"


def test_s1_uses_systematic_content_word_deletion() -> None:
    scenario = "Asha brings a notebook to support Omar after lunch."
    model = _target_model_flips_when(lambda candidate: "notebook" not in candidate.lower())

    result = S1WordGreedyStrategy().generate(
        scenario=scenario,
        choices=CHOICES,
        model=model,
        foil="C",
        budget=10,
    )

    assert result.status == "success"
    assert result.modified_scenario is not None
    assert "notebook" not in result.modified_scenario.lower()
    assert any(attempt.edit_description == "delete 'notebook'" for attempt in result.attempts)
