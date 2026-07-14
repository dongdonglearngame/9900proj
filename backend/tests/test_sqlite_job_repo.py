from collections.abc import Generator
from copy import deepcopy

import pytest
from sqlmodel import Session, SQLModel

from app.db.models import CounterfactualJob as CounterfactualJobRecord
from app.db.session import create_configured_engine
from app.repositories.checkpointing_job_repo import CheckpointingJobRepository
from app.repositories.job_repo import JobRepository
from app.repositories.sqlite_job_repo import RESULT_NOT_RESTORED_MESSAGE, SQLiteJobRepository
from app.schemas.counterfactual import (
    CounterfactualCreateRequest,
    CounterfactualJobResponse,
    CounterfactualProgress,
)


def make_request() -> CounterfactualCreateRequest:
    return CounterfactualCreateRequest(
        question_id="q1",
        experiment_run_id="run_demo_b",
        scenario="Regina is worried about her friend.",
        choices={
            "A": "Ignore the friend",
            "B": "Send a short reply",
            "C": "Offer to listen",
            "D": "Change the subject",
        },
        model="mock",
        original_answer="A",
        foil="C",
        strategy_id="s1_word_greedy",
        budget=20,
    )


def make_job(
    *,
    status: str = "pending",
    phase: str = "queued",
    search_calls: int = 0,
    postprocess_calls: int = 0,
    proposer_calls: int = 0,
    message: str | None = "queued",
) -> CounterfactualJobResponse:
    return CounterfactualJobResponse(
        job_id="job_test",
        status=status,  # type: ignore[arg-type]
        phase=phase,  # type: ignore[arg-type]
        progress=CounterfactualProgress(
            budget=20,
            search_calls=search_calls,
            postprocess_calls=postprocess_calls,
            proposer_calls=proposer_calls,
        ),
        result=None,
        message=message,
    )


@pytest.fixture
def sqlite_session_factory(tmp_path):
    engine = create_configured_engine(f"sqlite:///{tmp_path / 'jobs.db'}")
    SQLModel.metadata.create_all(engine)

    def factory() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    return engine, factory


def test_sqlite_engine_uses_wal_for_file_databases(sqlite_session_factory) -> None:
    engine, _factory = sqlite_session_factory

    with engine.connect() as connection:
        journal_mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar_one()

    assert journal_mode.lower() == "wal"


def test_sqlite_job_repository_round_trips_job_checkpoints(sqlite_session_factory) -> None:
    engine, factory = sqlite_session_factory
    repo = SQLiteJobRepository(session_factory=factory)

    repo.create(make_job(), request=make_request())
    with Session(engine) as session:
        record = session.get(CounterfactualJobRecord, "job_test")
        assert record is not None
        assert record.experiment_run_id == "run_demo_b"

    repo.set(make_job(status="running", phase="search", search_calls=3, message="testing"))
    running = repo.get("job_test")

    assert running is not None
    assert running.status == "running"
    assert running.phase == "search"
    assert running.progress.search_calls == 3
    assert running.message == "testing"
    assert running.result is None

    repo.set(
        make_job(
            status="completed",
            phase="done",
            search_calls=5,
            postprocess_calls=1,
            message=None,
        )
    )
    completed = repo.get("job_test")

    assert completed is not None
    assert completed.status == "completed"
    assert completed.progress.search_calls == 5
    assert completed.progress.postprocess_calls == 1
    assert completed.result is None
    assert completed.message == RESULT_NOT_RESTORED_MESSAGE


def test_sqlite_job_repository_requires_request_on_create(sqlite_session_factory) -> None:
    _engine, factory = sqlite_session_factory
    repo = SQLiteJobRepository(session_factory=factory)

    with pytest.raises(ValueError, match="requires the original request"):
        repo.create(make_job())


class FakeDbJobRepository:
    def __init__(self) -> None:
        self.created: list[CounterfactualJobResponse] = []
        self.flushed: list[CounterfactualJobResponse] = []

    def create(
        self,
        job: CounterfactualJobResponse,
        *,
        request: CounterfactualCreateRequest | None = None,
    ) -> None:
        self.created.append(deepcopy(job))

    def set(self, job: CounterfactualJobResponse) -> None:
        self.flushed.append(deepcopy(job))

    def get(self, job_id: str) -> CounterfactualJobResponse | None:
        return None


def test_checkpointing_job_repository_throttles_sqlite_writes() -> None:
    db = FakeDbJobRepository()
    repo = CheckpointingJobRepository(
        memory=JobRepository(),
        db=db,  # type: ignore[arg-type]
        flush_call_interval=5,
    )

    repo.create(make_job(), request=make_request())
    repo.set(make_job(status="running", phase="search", search_calls=1, message="testing"))
    repo.set(make_job(status="running", phase="search", search_calls=3, message="testing"))
    repo.set(make_job(status="running", phase="search", search_calls=6, message="testing"))
    repo.set(
        make_job(
            status="running",
            phase="postprocess",
            search_calls=6,
            postprocess_calls=1,
            message="finalizing",
        )
    )
    repo.set(
        make_job(
            status="completed",
            phase="done",
            search_calls=6,
            postprocess_calls=2,
            message=None,
        )
    )

    assert len(db.created) == 1
    assert [(job.phase, job.progress.search_calls) for job in db.flushed] == [
        ("search", 1),
        ("search", 6),
        ("postprocess", 6),
        ("done", 6),
    ]
