from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager

from sqlmodel import Session

from app.db.models import CounterfactualJob as CounterfactualJobRecord
from app.db.models import utc_now
from app.db.session import get_session
from app.schemas.counterfactual import (
    CounterfactualCreateRequest,
    CounterfactualJobResponse,
    CounterfactualProgress,
)

RESULT_NOT_RESTORED_MESSAGE = "result payload not restored (P18-12/13)"


class SQLiteJobRepository:
    """SQLite-backed checkpoint store for counterfactual job status."""

    def __init__(
        self,
        session_factory: Callable[[], Generator[Session, None, None]] = get_session,
    ) -> None:
        self._session_factory = session_factory

    def create(
        self,
        job: CounterfactualJobResponse,
        *,
        request: CounterfactualCreateRequest | None = None,
    ) -> None:
        if request is None:
            raise ValueError("SQLiteJobRepository.create requires the original request")

        record = CounterfactualJobRecord(
            id=job.job_id,
            experiment_run_id=request.experiment_run_id,
            status=job.status,
            phase=job.phase,
            strategy_id=request.strategy_id,
            model=request.model,
            foil=request.foil,
            budget=request.budget,
            search_calls=job.progress.search_calls,
            postprocess_calls=job.progress.postprocess_calls,
            proposer_calls=job.progress.proposer_calls,
            message=job.message,
            error_message=job.message if job.status == "failed" else None,
        )
        with self._session() as session:
            session.merge(record)
            session.commit()

    def set(self, job: CounterfactualJobResponse) -> None:
        with self._session() as session:
            record = session.get(CounterfactualJobRecord, job.job_id)
            if record is None:
                return

            record.status = job.status
            record.phase = job.phase
            record.search_calls = job.progress.search_calls
            record.postprocess_calls = job.progress.postprocess_calls
            record.proposer_calls = job.progress.proposer_calls
            record.message = job.message
            record.error_message = job.message if job.status == "failed" else None
            record.updated_at = utc_now()
            session.add(record)
            session.commit()

    def get(self, job_id: str) -> CounterfactualJobResponse | None:
        with self._session() as session:
            record = session.get(CounterfactualJobRecord, job_id)
            if record is None:
                return None

            message = record.message
            if record.status in {"completed", "failed"} and record.result_id is None:
                message = message or record.error_message or RESULT_NOT_RESTORED_MESSAGE

            return CounterfactualJobResponse(
                job_id=record.id,
                status=record.status,  # type: ignore[arg-type]
                phase=record.phase,  # type: ignore[arg-type]
                progress=CounterfactualProgress(
                    budget=record.budget,
                    search_calls=record.search_calls,
                    postprocess_calls=record.postprocess_calls,
                    proposer_calls=record.proposer_calls,
                ),
                result=None,
                message=message,
            )

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session_iterator = self._session_factory()
        session = next(session_iterator)
        try:
            yield session
        finally:
            session.close()
            session_iterator.close()
