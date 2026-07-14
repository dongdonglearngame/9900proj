from collections.abc import Generator

from sqlalchemy import inspect
from sqlmodel import Session

from app.db.init_db import init_db
from app.db.session import create_configured_engine
from app.repositories.sqlite_prediction_repo import SQLitePredictionRepository


def _create_sprint_one_schema(engine) -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE predictions (
                id VARCHAR NOT NULL PRIMARY KEY,
                cache_key VARCHAR NOT NULL UNIQUE,
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
        connection.exec_driver_sql(
            """
            INSERT INTO predictions (
                id, cache_key, question_id, scenario_hash, choices_hash, model,
                prompt_template_version, endpoint_type, answer, status, raw_response,
                option_logprobs_json, option_probs_json, top_logprobs_raw_json,
                runtime_seconds, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-id",
                "legacy-key",
                "q1",
                "scenario-hash",
                "choices-hash",
                "mock",
                "target-v2",
                "mock",
                "A",
                "ok",
                "A",
                '{"A": -0.1, "B": null}',
                '{"A": 0.9, "B": null}',
                "[]",
                0.1,
                "2026-01-01 00:00:00.000000",
            ),
        )
        for table in ("counterfactual_jobs", "counterfactuals", "metrics"):
            connection.exec_driver_sql(
                f'CREATE TABLE "{table}" (id VARCHAR NOT NULL PRIMARY KEY)'
            )


def test_init_db_migrates_sprint_one_schema_idempotently(tmp_path) -> None:
    engine = create_configured_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    _create_sprint_one_schema(engine)

    init_db(engine)
    init_db(engine)

    inspector = inspect(engine)
    prediction_columns = {column["name"] for column in inspector.get_columns("predictions")}
    assert {"top_logprobs", "target_num_predict", "temperature", "answer_text"} <= (
        prediction_columns
    )

    for table in ("counterfactual_jobs", "counterfactuals", "metrics"):
        columns = {column["name"] for column in inspector.get_columns(table)}
        indexes = {index["name"] for index in inspector.get_indexes(table)}
        assert "experiment_run_id" in columns
        assert f"ix_{table}_experiment_run_id" in indexes

    with engine.connect() as connection:
        versions = connection.exec_driver_sql(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).all()
    assert versions == [(1,)]

    def session_factory() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    restored = SQLitePredictionRepository(session_factory=session_factory).get("legacy-key")
    assert restored is not None
    assert restored.answer == "A"
    assert restored.answer_text is None
    assert restored.option_logprobs == {"A": -0.1, "B": None}
