from collections.abc import Generator

from sqlmodel import Session, SQLModel

from app.db.session import create_configured_engine
from app.repositories.checkpointing_job_repo import CheckpointingJobRepository
from app.repositories.factory import RepositoryFactory
from app.repositories.job_repo import JobRepository


def test_memory_factory_reuses_repository_instances() -> None:
    factory = RepositoryFactory(repo_backend="memory", initialise_sqlite=False)

    assert isinstance(factory.get_job_repository(), JobRepository)
    assert factory.get_job_repository() is factory.get_job_repository()
    assert factory.get_prediction_repository() is factory.get_prediction_repository()
    assert factory.get_scenario_repository() is factory.get_scenario_repository()


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
