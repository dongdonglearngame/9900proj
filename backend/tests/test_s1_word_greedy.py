from fastapi.testclient import TestClient

from app.llm.mock_client import MockLLMClient
from app.main import app
from app.strategies.base import CounterfactualRequest
from app.strategies.s1_word_greedy import S1WordGreedyStrategy

CHOICES = {
    "A": "Ignore the texts and continue sleeping",
    "B": "Tell her friend to seek professional help",
    "C": "Stay up and lend a listening ear",
    "D": "Suggest her friend find a new partner",
}


def test_s1_finds_regina_demo_edit() -> None:
    request = CounterfactualRequest(
        question_id="q_regina_001",
        scenario=(
            "Regina's best friend recently broke up with her longtime partner and is "
            "texting Regina in the middle of the night expressing feelings of loneliness."
        ),
        choices=CHOICES,
        model="mock",
        original_answer="A",
        foil="C",
        budget=20,
    )

    result = S1WordGreedyStrategy().generate(request, MockLLMClient().predict)

    assert result.status == "success"
    assert result.new_answer == "C"
    assert result.modified_scenario is not None
    assert "early evening" in result.modified_scenario
    assert len(result.attempts) == 1
    assert result.attempts[0].success


def test_s1_respects_zero_budget() -> None:
    request = CounterfactualRequest(
        question_id="q_regina_001",
        scenario=(
            "Regina's best friend recently broke up with her longtime partner and is "
            "texting Regina in the middle of the night expressing feelings of loneliness."
        ),
        choices=CHOICES,
        model="mock",
        original_answer="A",
        foil="C",
        budget=0,
    )

    def fail_if_called(scenario: str, choices: dict[str, str], model: str):
        raise AssertionError("target_predict should not be called when budget is zero")

    result = S1WordGreedyStrategy().generate(request, fail_if_called)

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
