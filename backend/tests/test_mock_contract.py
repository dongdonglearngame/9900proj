"""Locks the mock API contract the team builds against (no Ollama, no DB needed)."""

from fastapi.testclient import TestClient

from app.main import app

REGINA = {
    "question_id": "q_regina_001",
    "scenario": (
        "Regina's best friend recently broke up with her longtime partner and is "
        "texting Regina in the middle of the night expressing feelings of loneliness."
    ),
    "choices": {
        "A": "Ignore the texts and continue sleeping",
        "B": "Tell her friend to seek professional help",
        "C": "Stay up and lend a listening ear",
        "D": "Suggest her friend find a new partner",
    },
    "model": "mock",
}


def test_predict_returns_a_letter() -> None:
    response = TestClient(app).post("/predict", json=REGINA)
    assert response.status_code == 200
    assert response.json()["answer"] in {"A", "B", "C", "D"}


def test_counterfactual_mock_flow_completes() -> None:
    client = TestClient(app)
    created = client.post(
        "/counterfactual",
        json={**REGINA, "original_answer": "A", "foil": "C", "strategy_id": "s1_word_greedy"},
    ).json()
    job = client.get(f"/counterfactual/jobs/{created['job_id']}").json()
    assert job["status"] == "completed"
    assert job["result"] is not None
    # mock placeholder flips Regina A -> C so the explanation view is demoable
    assert job["result"]["status"] == "success"
    assert job["result"]["new_answer"] == "C"


def test_unknown_job_returns_404() -> None:
    assert TestClient(app).get("/counterfactual/jobs/nope").status_code == 404
