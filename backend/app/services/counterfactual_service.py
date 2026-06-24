from time import perf_counter
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
from app.strategies.base import CounterfactualResult, FrozenTargetModel
from app.strategies.registry import get_strategy


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
    """Orchestrates counterfactual jobs through the strategy registry."""

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
        started = perf_counter()
        context = CounterfactualRunContext(self._prediction_service, request.budget)
        self._job_repo.set(
            CounterfactualJobResponse(
                job_id=job_id,
                status="running",
                phase="search",
                progress=context.progress(),
                result=None,
                message="testing candidate edits",
            )
        )

        try:
            original_prediction = self._original_snapshot(request)
            strategy = get_strategy(request.strategy_id)
            target_model = FrozenTargetModel(
                model_id=request.model,
                target_predict_fn=context.target_predict,
            )

            raw_result = strategy.generate(
                scenario=request.scenario,
                choices=request.choices,
                model=target_model,
                foil=request.foil,
                budget=request.budget,
            )
            context.set_phase("postprocess")
            processed_result = self._postprocessor.process(
                raw_result,
                scenario=request.scenario,
                choices=request.choices,
                model=target_model,
                foil=request.foil,
                budget=request.budget,
            )
            context.set_phase("metrics")
            payload = self._build_payload(
                result=processed_result,
                context=context,
                runtime_seconds=round(perf_counter() - started, 4),
                original_prediction=original_prediction,
                original_answer=request.original_answer,
            )
            self._counterfactual_repo.add(payload)
            self._metrics_repo.add(payload.metrics)
            self._job_repo.set(
                CounterfactualJobResponse(
                    job_id=job_id,
                    status="completed",
                    phase="done",
                    progress=context.progress(),
                    result=payload,
                    message=None,
                )
            )
        except Exception as exc:
            self._job_repo.set(
                CounterfactualJobResponse(
                    job_id=job_id,
                    status="failed",
                    phase="failed",
                    progress=context.progress(),
                    result=None,
                    message=str(exc),
                )
            )

    def _original_snapshot(self, request: CounterfactualCreateRequest) -> PredictionSnapshot:
        prediction = self._prediction_service.target_predict(
            scenario=request.scenario,
            choices=request.choices,
            model=request.model,
        )
        return PredictionSnapshot(
            answer=prediction.answer or request.original_answer,
            option_logprobs=prediction.option_logprobs,
        )

    def _build_payload(
        self,
        *,
        result: CounterfactualResult,
        context: CounterfactualRunContext,
        runtime_seconds: float,
        original_prediction: PredictionSnapshot,
        original_answer: str,
    ) -> CounterfactualResultPayload:
        successful_attempt = next((attempt for attempt in result.attempts if attempt.success), None)
        new_prediction = None
        if successful_attempt and successful_attempt.prediction:
            new_prediction = PredictionSnapshot(
                answer=successful_attempt.prediction.answer,
                option_logprobs=successful_attempt.prediction.option_logprobs,
            )

        metrics = compute_counterfactual_metrics(
            original=result.original_scenario,
            modified=result.modified_scenario,
            flip_success=result.status == "success",
            search_calls=context.search_calls,
            postprocess_calls=context.postprocess_calls,
            proposer_calls=context.proposer_calls,
            runtime_seconds=runtime_seconds,
        )

        return CounterfactualResultPayload(
            status=result.status,
            strategy_id=result.strategy_id,
            original_answer=original_answer,
            foil=result.foil,
            new_answer=result.new_answer,
            original_scenario=result.original_scenario,
            modified_scenario=result.modified_scenario,
            original_prediction=original_prediction,
            new_prediction=new_prediction,
            diff=word_diff(result.original_scenario, result.modified_scenario),
            metrics=metrics,
            message=result.message,
        )
