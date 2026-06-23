from copy import deepcopy

from app.schemas.counterfactual import CounterfactualJobResponse


class JobRepository:
    """In-memory counterfactual job store.

    TODO(P18-CF-2): back this with the `counterfactual_jobs` table so jobs survive
    restarts and work across workers.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, CounterfactualJobResponse] = {}

    def create(self, job: CounterfactualJobResponse) -> None:
        self._jobs[job.job_id] = job

    def set(self, job: CounterfactualJobResponse) -> None:
        self._jobs[job.job_id] = job

    def get(self, job_id: str) -> CounterfactualJobResponse | None:
        job = self._jobs.get(job_id)
        return deepcopy(job) if job else None
