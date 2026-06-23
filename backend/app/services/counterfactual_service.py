from uuid import uuid4

from app.harness.target_predict import PredictionResult
from app.metrics.diff import word_diff
from app.metrics.scorer import compute_counterfactual_metrics
from app.repositories.counterfactual_repo import CounterfactualRepository
from app.repositories.job_repo import JobRepository
from app.repositories.metrics_repo import MetricsRepository
from app.schemas.counterfactual import (
    CounterfactualCreateRequest,
    CounterfactualCreateResponse,
    CounterfactualJobResponse,
    CounterfactualProgress,
    CounterfactualResultPayload,
    PredictionSnapshot,
)
from app.services.postprocessor import IdentityPostProcessor
from app.services.prediction_service import PredictionService, get_prediction_service


class CounterfactualRunContext:
    """Counting wrapper that a strategy's target_predict calls go through, so the job can
    report search vs post-process calls separately.

    Kept as the interface for the real orchestration. TODO(P18-CF-2): also push
    phase/progress updates to the job store as calls happen.
    """

    def __init__(self, prediction_service: PredictionService, budget: int) -> None:
        self.prediction_service = prediction_service
        self.budget = budget
        self.phase = "search"
        self.search_calls = 0
        self.postprocess_calls = 0
        self.proposer_calls = 0

    def set_phase(self, phase: str) -> None:
        self.phase = phase

    def target_predict(
        self, scenario: str, choices: dict[str, str], model: str
    ) -> PredictionResult:
        if self.phase == "postprocess":
            self.postprocess_calls += 1
        else:
            self.search_calls += 1
        return self.prediction_service.target_predict(
            scenario=scenario, choices=choices, model=model
        )

    def record_proposer_call(self) -> None:
        self.proposer_calls += 1

    def progress(self) -> CounterfactualProgress:
        return CounterfactualProgress(
            budget=self.budget,
            search_calls=self.search_calls,
            postprocess_calls=self.postprocess_calls,
            proposer_calls=self.proposer_calls,
        )


class CounterfactualService:
    """Orchestrates counterfactual jobs.

    TODO(P18-CF-2): replace the mock `run_job` below with the real pipeline:
        route -> create_job -> background run_job:
          context = CounterfactualRunContext(...)
          strategy = registry.get_strategy(request.strategy_id)
          raw = strategy.generate(request, context.target_predict)
          processed = post_processor.process(raw, ...)        # shared minimiser/fluency
          metrics = compute_counterfactual_metrics(...)        # shared metrics
          persist counterfactual + metrics; mark job completed
    Strategies must only verify flips through the frozen harness (context.target_predict),
    which never sees the foil.
    """

    def __init__(self) -> None:
        self._job_repo = JobRepository()
        self._counterfactual_repo = CounterfactualRepository()
        self._metrics_repo = MetricsRepository()
        self._prediction_service = get_prediction_service()
        self._postprocessor = IdentityPostProcessor()

    def create_job(self, request: CounterfactualCreateRequest) -> CounterfactualCreateResponse:
        job_id = f"job_{uuid4().hex[:12]}"
        self._job_repo.create(
            CounterfactualJobResponse(
                job_id=job_id,
                status="pending",
                phase="queued",
                progress=CounterfactualProgress(
                    budget=request.budget,
                    search_calls=0,
                    postprocess_calls=0,
                    proposer_calls=0,
                ),
                result=None,
                message="queued",
            )
        )
        return CounterfactualCreateResponse(job_id=job_id, status="pending")

    def get_job(self, job_id: str) -> CounterfactualJobResponse | None:
        return self._job_repo.get(job_id)

    def run_job(self, job_id: str, request: CounterfactualCreateRequest) -> None:
        # MOCK placeholder so the API contract + the frontend explanation view are
        # demoable in mock mode. TODO(P18-CF-2): real orchestration via the strategy
        # registry + shared post-processing + metrics. TODO(P18-CF-3): once S1 exists,
        # the canned edit below is replaced by the real proposed edit.
        payload = self._mock_payload(request)
        flipped = payload.status == "success"
        self._job_repo.set(
            CounterfactualJobResponse(
                job_id=job_id,
                status="completed",
                phase="done",
                progress=CounterfactualProgress(
                    budget=request.budget,
                    search_calls=1 if flipped else request.budget,
                    postprocess_calls=0,
                    proposer_calls=0,
                ),
                result=payload,
                message=None,
            )
        )

    def _mock_payload(
        self, request: CounterfactualCreateRequest
    ) -> CounterfactualResultPayload:
        # Trivial canned edit just for the mock demo (NOT the S1 algorithm).
        modified = request.scenario.replace("middle of the night", "early evening")
        flipped = modified != request.scenario
        original_prediction = PredictionSnapshot(
            answer=request.original_answer,
            option_logprobs={"A": -0.12, "B": -3.40, "C": -2.05, "D": None},
        )
        metrics = compute_counterfactual_metrics(
            original=request.scenario,
            modified=modified if flipped else None,
            flip_success=flipped,
            search_calls=1 if flipped else request.budget,
            postprocess_calls=0,
            proposer_calls=0,
            runtime_seconds=0.0,
        )
        if not flipped:
            return CounterfactualResultPayload(
                status="not_found",
                strategy_id=request.strategy_id,
                original_answer=request.original_answer,
                foil=request.foil,
                new_answer=None,
                original_scenario=request.scenario,
                modified_scenario=None,
                original_prediction=original_prediction,
                new_prediction=None,
                diff=[],
                metrics=metrics,
                message="mock: no canned edit for this scenario (real strategy is P18-CF-3)",
            )
        return CounterfactualResultPayload(
            status="success",
            strategy_id=request.strategy_id,
            original_answer=request.original_answer,
            foil=request.foil,
            new_answer=request.foil,
            original_scenario=request.scenario,
            modified_scenario=modified,
            original_prediction=original_prediction,
            new_prediction=PredictionSnapshot(
                answer=request.foil,
                option_logprobs={"A": -2.90, "B": -3.10, "C": -0.35, "D": None},
            ),
            diff=word_diff(request.scenario, modified),
            metrics=metrics,
            message="mock placeholder result (real orchestration is P18-CF-2)",
        )
