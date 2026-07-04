from app.repositories.job_repo import JobRepository
from app.repositories.sqlite_job_repo import SQLiteJobRepository
from app.schemas.counterfactual import CounterfactualCreateRequest, CounterfactualJobResponse

TERMINAL_STATUSES = {"completed", "failed"}


class CheckpointingJobRepository:
    """Live in-memory jobs with throttled SQLite checkpoints."""

    def __init__(
        self,
        *,
        memory: JobRepository,
        db: SQLiteJobRepository,
        flush_call_interval: int = 5,
    ) -> None:
        self._memory = memory
        self._db = db
        self._flush_call_interval = flush_call_interval
        self._last_flushed_phase: dict[str, str] = {}
        self._last_flushed_calls: dict[str, int] = {}

    def create(
        self,
        job: CounterfactualJobResponse,
        *,
        request: CounterfactualCreateRequest | None = None,
    ) -> None:
        self._memory.create(job, request=request)
        self._db.create(job, request=request)
        self._mark_flushed(job)

    def set(self, job: CounterfactualJobResponse) -> None:
        self._memory.set(job)
        if self._should_flush(job):
            self._db.set(job)
            self._mark_flushed(job)

    def get(self, job_id: str) -> CounterfactualJobResponse | None:
        return self._memory.get(job_id) or self._db.get(job_id)

    def _should_flush(self, job: CounterfactualJobResponse) -> bool:
        if job.status in TERMINAL_STATUSES:
            return True
        if self._last_flushed_phase.get(job.job_id) != job.phase:
            return True
        last_calls = self._last_flushed_calls.get(job.job_id, 0)
        return self._total_calls(job) - last_calls >= self._flush_call_interval

    def _mark_flushed(self, job: CounterfactualJobResponse) -> None:
        self._last_flushed_phase[job.job_id] = job.phase
        self._last_flushed_calls[job.job_id] = self._total_calls(job)

    def _total_calls(self, job: CounterfactualJobResponse) -> int:
        return (
            job.progress.search_calls
            + job.progress.postprocess_calls
            + job.progress.proposer_calls
        )
