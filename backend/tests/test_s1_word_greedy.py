from fastapi.testclient import TestClient

from app.harness.target_predict import PredictionResult
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


def _prediction(answer: str) -> PredictionResult:
    return PredictionResult(
        status="ok",
        answer=answer,
        answer_text=CHOICES.get(answer),
        model="mock",
        prompt_template_version="test",
        cache_hit=False,
        raw_response=answer,
        option_logprobs={"A": -2.0 if answer == "C" else -0.1, "B": None, "C": -0.1, "D": None},
        option_probs={"A": 0.1 if answer == "C" else 0.8, "B": None, "C": 0.8, "D": None},
        top_logprobs_raw=[],
        runtime_seconds=0.0,
    )


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


def test_s1_uses_systematic_emotion_replacement_beyond_demo_seed() -> None:
    request = CounterfactualRequest(
        question_id="q_systematic_emotion",
        scenario="Maya feels panicked after a classmate ignores her message.",
        choices=CHOICES,
        model="mock",
        original_answer="A",
        foil="C",
        budget=20,
    )

    def target_predict(scenario: str, choices: dict[str, str], model: str) -> PredictionResult:
        return _prediction("C" if "worried" in scenario else "A")

    result = S1WordGreedyStrategy().generate(request, target_predict)

    assert result.status == "success"
    assert result.modified_scenario is not None
    assert "worried" in result.modified_scenario
    assert result.attempts[-1].edit_description is not None
    assert result.attempts[-1].edit_description.startswith("emotion intensity substitution")


def test_s1_uses_systematic_content_word_deletion() -> None:
    request = CounterfactualRequest(
        question_id="q_systematic_deletion",
        scenario="Asha brings a notebook to support Omar after lunch.",
        choices=CHOICES,
        model="mock",
        original_answer="A",
        foil="C",
        budget=30,
    )

    def target_predict(scenario: str, choices: dict[str, str], model: str) -> PredictionResult:
        return _prediction("C" if "notebook" not in scenario else "A")

    result = S1WordGreedyStrategy().generate(request, target_predict)

    assert result.status == "success"
    assert result.modified_scenario is not None
    assert "notebook" not in result.modified_scenario
    assert result.attempts[-1].edit_description == "delete content word 'notebook'"


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
