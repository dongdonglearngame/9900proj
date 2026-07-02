from copy import deepcopy

from app.schemas.counterfactual import CounterfactualCreateRequest, CounterfactualJobResponse


class JobRepository:
    """In-memory counterfactual job store for mock and fast local runs."""

    def __init__(self) -> None:
        self._jobs: dict[str, CounterfactualJobResponse] = {}

    def create(
        self,
        job: CounterfactualJobResponse,
        *,
        request: CounterfactualCreateRequest | None = None,
    ) -> None:
        self._jobs[job.job_id] = job

    def set(self, job: CounterfactualJobResponse) -> None:
        self._jobs[job.job_id] = job

    def get(self, job_id: str) -> CounterfactualJobResponse | None:
        job = self._jobs.get(job_id)
        return deepcopy(job) if job else None
