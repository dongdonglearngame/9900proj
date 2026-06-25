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

SIX_CHOICE_SCENARIO = {
    "question_id": "q_dynamic_001",
    "scenario": "Someone texts in the early evening asking for emotional support.",
    "choices": {
        "A": "Ignore the message",
        "B": "Send a short reply later",
        "C": "Offer to listen and stay present",
        "D": "Tell them to solve it alone",
        "E": "Change the subject",
        "F": "Block the contact",
    },
    "model": "mock",
}


def test_predict_returns_a_letter() -> None:
    response = TestClient(app).post("/predict", json=REGINA)
    assert response.status_code == 200
    assert response.json()["answer"] in {"A", "B", "C", "D"}


def test_predict_accepts_six_choice_payloads() -> None:
    response = TestClient(app).post("/predict", json=SIX_CHOICE_SCENARIO)
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "C"
    assert set(body["option_logprobs"]) == set(SIX_CHOICE_SCENARIO["choices"])


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


def test_counterfactual_rejects_answers_outside_choices() -> None:
    response = TestClient(app).post(
        "/counterfactual",
        json={
            **SIX_CHOICE_SCENARIO,
            "original_answer": "A",
            "foil": "G",
            "strategy_id": "s1_word_greedy",
        },
    )
    assert response.status_code == 422


def test_unknown_job_returns_404() -> None:
    assert TestClient(app).get("/counterfactual/jobs/nope").status_code == 404
