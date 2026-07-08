from collections.abc import Generator

from sqlmodel import Session, SQLModel, select

from app.db.hashing import prediction_cache_key
from app.db.models import Prediction as PredictionRecord
from app.db.session import create_configured_engine
from app.harness.target_predict import PredictionResult
from app.repositories.sqlite_prediction_repo import SQLitePredictionRepository


def test_sqlite_prediction_repository_round_trips_prediction_payload(tmp_path) -> None:
    engine = create_configured_engine(f"sqlite:///{tmp_path / 'predictions.db'}")
    SQLModel.metadata.create_all(engine)

    def session_factory() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    choices = {"A": "Ignore", "B": "Listen", "C": "Ask for help", "D": "Leave"}
    scenario = "Regina is worried about her friend."
    cache_key = prediction_cache_key(
        model="mock",
        prompt_template_version="target-v2",
        scenario=scenario,
        choices=choices,
        endpoint_type="mock",
        top_logprobs=20,
        target_num_predict=4,
    )
    result = PredictionResult(
        status="ok",
        answer="B",
        answer_text="Listen",
        model="mock",
        prompt_template_version="target-v2",
        cache_hit=False,
        raw_response="B",
        option_logprobs={"A": -3.1, "B": -0.2, "C": None, "D": -4.0},
        option_probs={"A": 0.04, "B": 0.82, "C": None, "D": 0.01},
        top_logprobs_raw=[{"top_logprobs": [{"token": "B", "logprob": -0.2}]}],
        runtime_seconds=0.12,
    )

    repo = SQLitePredictionRepository(session_factory=session_factory)
    repo.set(
        cache_key,
        result,
        question_id="q1",
        scenario=scenario,
        choices=choices,
        endpoint_type="mock",
        top_logprobs=20,
        target_num_predict=4,
    )

    restored = SQLitePredictionRepository(session_factory=session_factory).get(cache_key)

    assert restored == result
    with Session(engine) as session:
        record = session.exec(select(PredictionRecord)).one()
        assert record.question_id == "q1"
        assert record.endpoint_type == "mock"
        assert record.top_logprobs == 20
        assert record.target_num_predict == 4
        assert record.answer_text == "Listen"
