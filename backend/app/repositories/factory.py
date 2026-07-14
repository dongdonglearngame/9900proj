from collections.abc import Callable, Generator
from functools import lru_cache
from typing import Literal

from sqlmodel import Session

from app.core.config import get_settings
from app.db.init_db import init_db
from app.db.session import get_session
from app.repositories.checkpointing_job_repo import CheckpointingJobRepository
from app.repositories.counterfactual_repo import CounterfactualRepository
from app.repositories.experiment_run_repo import (
    ExperimentRunRepository,
    InMemoryExperimentRunRepository,
)
from app.repositories.job_repo import JobRepository
from app.repositories.metrics_repo import MetricsRepository
from app.repositories.prediction_repo import PredictionRepository
from app.repositories.scenario_repo import ScenarioRepository
from app.repositories.sqlite_job_repo import SQLiteJobRepository
from app.repositories.sqlite_prediction_repo import SQLitePredictionRepository

RepoBackend = Literal["memory", "sqlite"]
ExperimentRunStore = ExperimentRunRepository | InMemoryExperimentRunRepository


class RepositoryFactory:
    """Creates shared repositories for the configured backend."""

    def __init__(
        self,
        *,
        repo_backend: RepoBackend | None = None,
        session_factory: Callable[[], Generator[Session, None, None]] = get_session,
        initialise_sqlite: bool = True,
    ) -> None:
        self._repo_backend: RepoBackend = repo_backend or get_settings().repo_backend
        self._session_factory = session_factory
        self._initialise_sqlite = initialise_sqlite
        self._instances: dict[str, object] = {}
        if self._repo_backend == "sqlite" and self._initialise_sqlite:
            init_db()

    def get_prediction_repository(self) -> PredictionRepository:
        if self._repo_backend == "sqlite":
            return self._get(
                "prediction",
                lambda: SQLitePredictionRepository(session_factory=self._session_factory),
            )
        return self._get("prediction", PredictionRepository)

    def get_experiment_run_repository(self) -> ExperimentRunStore:
        if self._repo_backend == "sqlite":
            return self._get(
                "experiment_run",
                lambda: ExperimentRunRepository(session_factory=self._session_factory),
            )
        return self._get("experiment_run", InMemoryExperimentRunRepository)

    def get_job_repository(self) -> JobRepository | CheckpointingJobRepository:
        if self._repo_backend == "sqlite":
            return self._get(
                "job",
                lambda: CheckpointingJobRepository(
                    memory=JobRepository(),
                    db=SQLiteJobRepository(session_factory=self._session_factory),
                ),
            )
        return self._get("job", JobRepository)

    def get_counterfactual_repository(self) -> CounterfactualRepository:
        # Full result persistence is kept for P18-12/P18-13.
        return self._get("counterfactual", CounterfactualRepository)

    def get_metrics_repository(self) -> MetricsRepository:
        # Aggregated metrics persistence is kept for P18-9/P18-13.
        return self._get("metrics", MetricsRepository)

    def get_scenario_repository(self) -> ScenarioRepository:
        return self._get(
            "scenario",
            lambda: ScenarioRepository(session_factory=self._session_factory),
        )

    def _get(self, key: str, factory: Callable[[], object]):
        if key not in self._instances:
            self._instances[key] = factory()
        return self._instances[key]


@lru_cache
def get_repository_factory() -> RepositoryFactory:
    return RepositoryFactory()


@lru_cache
def get_prediction_repository() -> PredictionRepository:
    return get_repository_factory().get_prediction_repository()


@lru_cache
def get_experiment_run_repository() -> ExperimentRunStore:
    return get_repository_factory().get_experiment_run_repository()


@lru_cache
def get_job_repository() -> JobRepository | CheckpointingJobRepository:
    return get_repository_factory().get_job_repository()


@lru_cache
def get_counterfactual_repository() -> CounterfactualRepository:
    return get_repository_factory().get_counterfactual_repository()


@lru_cache
def get_metrics_repository() -> MetricsRepository:
    return get_repository_factory().get_metrics_repository()


@lru_cache
def get_scenario_repository() -> ScenarioRepository:
    return get_repository_factory().get_scenario_repository()


def clear_repository_caches() -> None:
    get_prediction_repository.cache_clear()
    get_experiment_run_repository.cache_clear()
    get_job_repository.cache_clear()
    get_counterfactual_repository.cache_clear()
    get_metrics_repository.cache_clear()
    get_scenario_repository.cache_clear()
    get_repository_factory.cache_clear()
