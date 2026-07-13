from fastapi.testclient import TestClient

from app.main import app

CHOICES = {
    "A": "Ignore the texts and continue sleeping",
    "B": "Tell her friend to seek professional help",
    "C": "Stay up and lend a listening ear",
    "D": "Suggest her friend find a new partner",
}

SELECTED_SCENARIO = {
    "question_id": "q_regina_001",
    "scenario_item_id": "s_regina_001",
    "task_type": "EU",
    "dimension": "emotion_cause",
    "subject": "Regina",
    "scenario": (
        "Regina's best friend recently broke up with her longtime partner and is "
        "texting Regina in the middle of the night expressing feelings of loneliness."
    ),
    "question_text": "What should Regina do?",
    "choices": CHOICES,
    "label": "C",
}


def test_comparison_api_runs_mock_batch_job() -> None:
    client = TestClient(app)

    created = client.post(
        "/comparison",
        json={
            "model": "mock",
            "strategy_ids": ["s1_word_greedy"],
            "selected_scenario": SELECTED_SCENARIO,
            "selected_question_id": "q_regina_001",
            "task_type": "EU",
            "limit": 1,
            "budget": 5,
            "foil_mode": "single",
        },
    )

    assert created.status_code == 200
    job = client.get(f"/comparison/jobs/{created.json()['job_id']}")
    assert job.status_code == 200
    body = job.json()
    assert body["status"] == "completed"
    assert body["result"]["selected_scenario"]["original_answer"] == "A"
    assert body["result"]["selected_scenario"]["foils"] == ["C"]
    assert body["result"]["summary"][0]["strategy_id"] == "s1_word_greedy"


def test_comparison_api_supports_batch_only_without_selected_scenario() -> None:
    client = TestClient(app)

    created = client.post(
        "/comparison",
        json={
            "model": "mock",
            "strategy_ids": ["s1_word_greedy"],
            "task_type": "EU",
            "limit": 1,
            "budget": 5,
            "foil_mode": "single",
        },
    )

    assert created.status_code == 200
    job = client.get(f"/comparison/jobs/{created.json()['job_id']}")
    assert job.status_code == 200
    body = job.json()
    assert body["status"] == "completed"
    assert body["result"]["selected_scenario"] is None
    assert body["result"]["summary"][0]["runs"] >= 1
