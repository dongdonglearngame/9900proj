from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session

from app.db.init_db import init_db
from app.db.session import create_configured_engine
from app.repositories.sqlite_prediction_repo import SQLitePredictionRepository


def test_init_db_migrates_existing_prediction_table(tmp_path) -> None:
    engine = create_configured_engine(f"sqlite:///{tmp_path / 'old_main.db'}")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE predictions (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    cache_key VARCHAR NOT NULL,
                    question_id VARCHAR,
                    scenario_hash VARCHAR NOT NULL,
                    choices_hash VARCHAR NOT NULL,
                    model VARCHAR NOT NULL,
                    prompt_template_version VARCHAR NOT NULL,
                    endpoint_type VARCHAR NOT NULL,
                    answer VARCHAR,
                    status VARCHAR NOT NULL,
                    raw_response VARCHAR NOT NULL,
                    option_logprobs_json VARCHAR NOT NULL,
                    option_probs_json VARCHAR NOT NULL,
                    top_logprobs_raw_json VARCHAR NOT NULL,
                    runtime_seconds FLOAT NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO predictions (
                    id,
                    cache_key,
                    question_id,
                    scenario_hash,
                    choices_hash,
                    model,
                    prompt_template_version,
                    endpoint_type,
                    answer,
                    status,
                    raw_response,
                    option_logprobs_json,
                    option_probs_json,
                    top_logprobs_raw_json,
                    runtime_seconds,
                    created_at
                )
                VALUES (
                    'old-key',
                    'old-key',
                    'q1',
                    'scenario-hash',
                    'choices-hash',
                    'mock',
                    'target-v1',
                    'mock',
                    'A',
                    'ok',
                    'A',
                    '{"A": -0.1}',
                    '{"A": 1.0}',
                    '[]',
                    0.01,
                    '2026-01-01 00:00:00'
                )
                """
            )
        )

    init_db(engine)

    with engine.connect() as connection:
        prediction_columns = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(predictions)")
        }

    assert {"top_logprobs", "target_num_predict", "answer_text"} <= prediction_columns

    def session_factory() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    restored = SQLitePredictionRepository(session_factory=session_factory).get("old-key")

    assert restored is not None
    assert restored.answer == "A"
    assert restored.answer_text is None
