from collections.abc import Generator

from sqlmodel import Session, SQLModel

from app.db.session import create_configured_engine
from app.repositories.checkpointing_job_repo import CheckpointingJobRepository
from app.repositories.experiment_run_repo import (
    ExperimentRunRepository,
    InMemoryExperimentRunRepository,
)
from app.repositories.factory import RepositoryFactory
from app.repositories.job_repo import JobRepository
from app.repositories.sqlite_prediction_repo import SQLitePredictionRepository


def test_memory_factory_reuses_repository_instances() -> None:
    factory = RepositoryFactory(repo_backend="memory", initialise_sqlite=False)

    assert isinstance(factory.get_job_repository(), JobRepository)
    assert factory.get_job_repository() is factory.get_job_repository()
    assert factory.get_prediction_repository() is factory.get_prediction_repository()
    assert factory.get_scenario_repository() is factory.get_scenario_repository()
    run_repo = factory.get_experiment_run_repository()
    assert isinstance(run_repo, InMemoryExperimentRunRepository)

    run = run_repo.create(
        name="memory-run",
        model="mock",
        budget=5,
        prompt_template_version="target-v2",
        strategy_ids=["s1_word_greedy"],
        git_commit="test-commit",
    )

    assert run_repo.get(run.id).git_commit == "test-commit"


def test_sqlite_factory_wraps_jobs_with_checkpointing_repo(tmp_path) -> None:
    engine = create_configured_engine(f"sqlite:///{tmp_path / 'factory.db'}")
    SQLModel.metadata.create_all(engine)

    def session_factory() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    factory = RepositoryFactory(
        repo_backend="sqlite",
        session_factory=session_factory,
        initialise_sqlite=False,
    )

    job_repo = factory.get_job_repository()
    assert isinstance(job_repo, CheckpointingJobRepository)
    assert job_repo is factory.get_job_repository()
    assert isinstance(factory.get_prediction_repository(), SQLitePredictionRepository)
    assert isinstance(factory.get_experiment_run_repository(), ExperimentRunRepository)
