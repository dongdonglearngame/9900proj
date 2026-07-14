from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from uuid import uuid4

from app.core.config import get_settings
from app.harness.target_predict import PredictionResult
from app.metrics.diff import word_diff
from app.metrics.scorer import compute_counterfactual_metrics
from app.proposer.clients import MockProposerClient, OllamaProposerClient
from app.proposer.harness import CandidateOutcome, ProposerHarness
from app.repositories.factory import (
    get_counterfactual_repository,
    get_job_repository,
    get_metrics_repository,
)
from app.schemas.counterfactual import (
    CounterfactualCreateRequest,
    CounterfactualCreateResponse,
    CounterfactualJobResponse,
    CounterfactualProgress,
    CounterfactualResultPayload,
    PredictionSnapshot,
)
from app.schemas.proposer import ProposerCallDiagnostics, ProposerDiagnostics
from app.services.postprocessor import IdentityPostProcessor
from app.services.prediction_service import PredictionService, get_prediction_service
from app.strategies.base import CounterfactualResult, FrozenTargetModel
from app.strategies.registry import get_strategy


class CounterfactualRunContext:
    """Counting wrapper that a strategy's target_predict calls go through, so the job can
    report search vs post-process calls separately.

    Kept as the interface for the real orchestration.
    """

    def __init__(self, prediction_service: PredictionService, budget: int) -> None:
        self.prediction_service = prediction_service
        self.budget = budget
        self.phase = "search"
        self.search_calls = 0
        self.postprocess_calls = 0
        self.proposer_calls = 0
        self._proposer_call_diagnostics: list[ProposerCallDiagnostics] = []
        self._unique_valid_candidates = 0
        self._target_verified_candidates = 0
        self._guard_rejections: dict[str, int] = {}
        self._update_hook: Callable[CounterfactualRunContext, None] | None = None

    def set_update_hook(self, update_hook: Callable[CounterfactualRunContext, None]) -> None:
        self._update_hook = update_hook

    def _notify(self) -> None:
        if self._update_hook is not None:
            self._update_hook(self)

    def set_phase(self, phase: str) -> None:
        self.phase = phase
        self._notify()

    def target_predict(
        self, scenario: str, choices: dict[str, str], model: str
    ) -> PredictionResult:
        if self.phase == "postprocess":
            self.postprocess_calls += 1
        else:
            self.search_calls += 1
        prediction = self.prediction_service.target_predict(
            scenario=scenario, choices=choices, model=model
        )
        self._notify()
        return prediction

    def record_proposer_call(self) -> None:
        self.proposer_calls += 1
        self._notify()

    def record_proposer_diagnostics(self, diagnostics: ProposerCallDiagnostics) -> None:
        self._proposer_call_diagnostics.append(diagnostics)

    def record_candidate_outcome(self, outcome: CandidateOutcome) -> None:
        if outcome == "unique_valid":
            self._unique_valid_candidates += 1
        elif outcome == "target_verified":
            self._target_verified_candidates += 1
        else:
            self._guard_rejections[outcome] = self._guard_rejections.get(outcome, 0) + 1

    def proposer_diagnostics(self) -> ProposerDiagnostics | None:
        if not self._proposer_call_diagnostics and not self._guard_rejections:
            return None

        requested = sum(item.requested_candidates for item in self._proposer_call_diagnostics)
        raw = sum(item.raw_candidates for item in self._proposer_call_diagnostics)
        parsed = sum(item.parsed_candidates for item in self._proposer_call_diagnostics)
        delivered = sum(
            item.delivered_candidates for item in self._proposer_call_diagnostics
        )
        return ProposerDiagnostics(
            calls=list(self._proposer_call_diagnostics),
            requested_candidates=requested,
            raw_candidates=raw,
            parsed_candidates=parsed,
            delivered_candidates=delivered,
            unique_valid_candidates=self._unique_valid_candidates,
            target_verified_candidates=self._target_verified_candidates,
            guard_rejections=dict(sorted(self._guard_rejections.items())),
            raw_requested_yield=_ratio(raw, requested),
            parsed_raw_yield=_ratio(parsed, raw),
            unique_valid_requested_yield=_ratio(
                self._unique_valid_candidates,
                requested,
            ),
            target_verified_parsed_yield=_ratio(
                self._target_verified_candidates,
                parsed,
            ),
            target_verified_delivered_yield=_ratio(
                self._target_verified_candidates,
                delivered,
            ),
        )

    def progress(self) -> CounterfactualProgress:
        return CounterfactualProgress(
            budget=self.budget,
            search_calls=self.search_calls,
            postprocess_calls=self.postprocess_calls,
            proposer_calls=self.proposer_calls,
        )


class CounterfactualService:
    """Orchestrates counterfactual jobs through the strategy registry."""

    _PHASE_MESSAGES = {
        "queued": "queued",
        "search": "testing candidate edits",
        "postprocess": "finalizing selected edit",
        "metrics": "scoring counterfactual result",
        "done": None,
        "failed": None,
    }

    def __init__(self) -> None:
        self._job_repo = get_job_repository()
        self._counterfactual_repo = get_counterfactual_repository()
        self._metrics_repo = get_metrics_repository()
        self._prediction_service = get_prediction_service()
        self._postprocessor = IdentityPostProcessor()

    def create_job(self, request: CounterfactualCreateRequest) -> CounterfactualCreateResponse:
        job_id = f"job_{uuid4().hex[:12]}"
        job = CounterfactualJobResponse(
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
        self._job_repo.create(job, request=request)
        return CounterfactualCreateResponse(job_id=job_id, status="pending")

    def get_job(self, job_id: str) -> CounterfactualJobResponse | None:
        return self._job_repo.get(job_id)

    def run_job(self, job_id: str, request: CounterfactualCreateRequest) -> None:
        context = CounterfactualRunContext(self._prediction_service, request.budget)
        context.set_update_hook(
            lambda updated_context: self._publish_running_job(job_id, updated_context)
        )
        self._publish_running_job(job_id, context)

        try:
            payload = self._run_with_context(request, context)
            self._store_payload(payload)
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

    def run_once(self, request: CounterfactualCreateRequest) -> CounterfactualResultPayload:
        """Run one counterfactual search synchronously for batch comparison."""
        context = CounterfactualRunContext(self._prediction_service, request.budget)
        payload = self._run_with_context(request, context)
        self._store_payload(payload)
        return payload

    def _store_payload(self, payload: CounterfactualResultPayload) -> None:
        self._counterfactual_repo.add(payload)
        self._metrics_repo.add(payload.metrics)

    def _run_with_context(
        self,
        request: CounterfactualCreateRequest,
        context: CounterfactualRunContext,
    ) -> CounterfactualResultPayload:
        started = perf_counter()
        original_prediction = self._original_snapshot(request)
        strategy = get_strategy(request.strategy_id)
        target_model = FrozenTargetModel(
            model_id=request.model,
            target_predict_fn=context.target_predict,
        )
        proposer = self._build_proposer(request, context)

        raw_result = strategy.generate(
            scenario=request.scenario,
            choices=request.choices,
            model=target_model,
            foil=request.foil,
            budget=request.budget,
            proposer=proposer,
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
        return self._build_payload(
            result=processed_result,
            context=context,
            runtime_seconds=round(perf_counter() - started, 4),
            original_prediction=original_prediction,
            original_answer=request.original_answer,
            experiment_run_id=request.experiment_run_id,
        )

    def _publish_running_job(self, job_id: str, context: CounterfactualRunContext) -> None:
        self._job_repo.set(
            CounterfactualJobResponse(
                job_id=job_id,
                status="running",
                phase=context.phase,
                progress=context.progress(),
                result=None,
                message=self._PHASE_MESSAGES.get(context.phase),
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

    def _build_proposer(
        self,
        request: CounterfactualCreateRequest,
        context: CounterfactualRunContext,
    ) -> ProposerHarness:
        settings = get_settings()
        client = (
            MockProposerClient()
            if settings.use_mock_llm
            else OllamaProposerClient(
                base_url=settings.ollama_base_url,
                model=settings.proposer_model,
            )
        )
        return ProposerHarness(
            client=client,
            original_answer=request.original_answer,
            temperature=settings.proposer_temperature,
            seed=settings.proposer_seed,
            num_predict=_proposer_num_predict(request.strategy_id),
            on_call=context.record_proposer_call,
            on_diagnostics=context.record_proposer_diagnostics,
            on_candidate_outcome=context.record_candidate_outcome,
        )

    def _build_payload(
        self,
        *,
        result: CounterfactualResult,
        context: CounterfactualRunContext,
        runtime_seconds: float,
        original_prediction: PredictionSnapshot,
        original_answer: str,
        experiment_run_id: str | None,
    ) -> CounterfactualResultPayload:
        successful_attempt = next((attempt for attempt in result.attempts if attempt.success), None)
        new_prediction = None
        if successful_attempt and successful_attempt.prediction:
            new_prediction = PredictionSnapshot(
                answer=successful_attempt.prediction.answer,
                option_logprobs=successful_attempt.prediction.option_logprobs,
            )

        candidate_foil_logprobs = [
            attempt.prediction.option_logprobs.get(result.foil)
            for attempt in result.attempts
            if attempt.prediction is not None
        ]
        selected_foil_logprob = (
            successful_attempt.prediction.option_logprobs.get(result.foil)
            if successful_attempt is not None and successful_attempt.prediction is not None
            else None
        )

        metrics = compute_counterfactual_metrics(
            original=result.original_scenario,
            modified=result.modified_scenario,
            flip_success=result.status == "success",
            search_calls=context.search_calls,
            postprocess_calls=context.postprocess_calls,
            proposer_calls=context.proposer_calls,
            runtime_seconds=runtime_seconds,
            original_foil_logprob=original_prediction.option_logprobs.get(result.foil),
            candidate_foil_logprobs=candidate_foil_logprobs,
            selected_foil_logprob=selected_foil_logprob,
        )
        metrics = metrics.model_copy(update={"experiment_run_id": experiment_run_id})

        return CounterfactualResultPayload(
            status=result.status,
            experiment_run_id=experiment_run_id,
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
            proposer_diagnostics=context.proposer_diagnostics(),
            message=result.message,
        )


def _proposer_num_predict(strategy_id: str) -> int:
    settings = get_settings()
    if strategy_id == "s2_llm_propose_verify":
        return settings.s2_proposer_num_predict
    if strategy_id == "s6_concept_causal_editing":
        return settings.s6_proposer_num_predict
    return settings.proposer_num_predict


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)
