import json
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from uuid import uuid4

from sqlmodel import Session

from app.db.git import get_git_commit
from app.db.models import ExperimentRun
from app.db.session import get_session


def _new_experiment_run(
    *,
    name: str,
    model: str,
    budget: int,
    prompt_template_version: str,
    strategy_ids: list[str],
    scenario_subset_id: str | None,
    task_type: str | None,
    dimension: str | None,
    git_commit: str | None,
    notes: str | None,
) -> ExperimentRun:
    return ExperimentRun(
        id=str(uuid4()),
        name=name,
        scenario_subset_id=scenario_subset_id,
        model=model,
        budget=budget,
        prompt_template_version=prompt_template_version,
        strategy_ids_json=json.dumps(strategy_ids, sort_keys=True),
        task_type=task_type,
        dimension=dimension,
        git_commit=git_commit if git_commit is not None else get_git_commit(),
        notes=notes,
    )


class ExperimentRunRepository:
    """Stores reproducible batch-comparison run metadata."""

    def __init__(
        self,
        session_factory: Callable[[], Generator[Session, None, None]] = get_session,
    ) -> None:
        self._session_factory = session_factory

    def create(
        self,
        *,
        name: str,
        model: str,
        budget: int,
        prompt_template_version: str,
        strategy_ids: list[str],
        scenario_subset_id: str | None = None,
        task_type: str | None = None,
        dimension: str | None = None,
        git_commit: str | None = None,
        notes: str | None = None,
    ) -> ExperimentRun:
        record = _new_experiment_run(
            name=name,
            scenario_subset_id=scenario_subset_id,
            model=model,
            budget=budget,
            prompt_template_version=prompt_template_version,
            strategy_ids=strategy_ids,
            task_type=task_type,
            dimension=dimension,
            git_commit=git_commit,
            notes=notes,
        )
        with self._session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def get(self, run_id: str) -> ExperimentRun | None:
        with self._session() as session:
            return session.get(ExperimentRun, run_id)

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session_iterator = self._session_factory()
        session = next(session_iterator)
        try:
            yield session
        finally:
            session.close()
            session_iterator.close()


class MemoryExperimentRunRepository:
    """In-memory ExperimentRun storage for mock and isolated test modes."""

    def __init__(self) -> None:
        self._runs: dict[str, ExperimentRun] = {}

    def create(
        self,
        *,
        name: str,
        model: str,
        budget: int,
        prompt_template_version: str,
        strategy_ids: list[str],
        scenario_subset_id: str | None = None,
        task_type: str | None = None,
        dimension: str | None = None,
        git_commit: str | None = None,
        notes: str | None = None,
    ) -> ExperimentRun:
        record = _new_experiment_run(
            name=name,
            scenario_subset_id=scenario_subset_id,
            model=model,
            budget=budget,
            prompt_template_version=prompt_template_version,
            strategy_ids=strategy_ids,
            task_type=task_type,
            dimension=dimension,
            git_commit=git_commit,
            notes=notes,
        )
        self._runs[record.id] = record.model_copy(deep=True)
        return record.model_copy(deep=True)

    def get(self, run_id: str) -> ExperimentRun | None:
        record = self._runs.get(run_id)
        return record.model_copy(deep=True) if record else None
