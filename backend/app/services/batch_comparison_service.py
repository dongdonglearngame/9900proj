from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from statistics import median
from uuid import uuid4

from app.core.config import get_settings
from app.harness.target_predict import PredictionResult
from app.repositories.factory import (
    ExperimentRunStore,
    get_experiment_run_repository,
    get_scenario_repository,
)
from app.schemas.common import ChoiceLetter, ordered_choice_letters
from app.schemas.comparison import (
    BatchComparisonResult,
    ComparisonCoverage,
    ComparisonCreateRequest,
    ComparisonCreateResponse,
    ComparisonJobResponse,
    ComparisonProgress,
    ComparisonRow,
    ComparisonStrategySummary,
    FoilMode,
    SelectedScenarioComparison,
)
from app.schemas.counterfactual import CounterfactualCreateRequest, CounterfactualResultPayload
from app.schemas.scenario import ScenarioItem
from app.services.counterfactual_service import CounterfactualService
from app.services.prediction_service import PredictionService, get_prediction_service
from app.strategies.registry import get_strategy

PAGE_SIZE = 100


@dataclass(frozen=True)
class ComparisonUnit:
    scenario: ScenarioItem
    prediction: PredictionResult
    strategy_id: str
    foil: ChoiceLetter


class BatchComparisonService:
    """Runs controlled strategy comparisons over one selected case and a batch."""

    def __init__(
        self,
        *,
        scenario_source=None,
        prediction_service: PredictionService | None = None,
        counterfactual_service: CounterfactualService | None = None,
        experiment_run_repository: ExperimentRunStore | None = None,
    ) -> None:
        self._scenario_source = (
            scenario_source if scenario_source is not None else get_scenario_repository()
        )
        self._prediction_service = (
            prediction_service
            if prediction_service is not None
            else get_prediction_service()
        )
        self._counterfactual_service = (
            counterfactual_service
            if counterfactual_service is not None
            else CounterfactualService()
        )
        self._experiment_run_repository = (
            experiment_run_repository
            if experiment_run_repository is not None
            else get_experiment_run_repository()
        )
        self._jobs: dict[str, ComparisonJobResponse] = {}

    def create_job(self, request: ComparisonCreateRequest) -> ComparisonCreateResponse:
        self._validate_strategy_ids(request.strategy_ids)
        job_id = f"comparison_{uuid4().hex[:12]}"
        experiment_run_id = self._create_experiment_run(request, name=job_id)
        self._jobs[job_id] = ComparisonJobResponse(
            job_id=job_id,
            experiment_run_id=experiment_run_id,
            status="pending",
            progress=ComparisonProgress(total_units=0, completed_units=0, skipped_units=0),
            result=None,
            message="queued",
        )
        return ComparisonCreateResponse(
            job_id=job_id,
            experiment_run_id=experiment_run_id,
            status="pending",
        )

    def get_job(self, job_id: str) -> ComparisonJobResponse | None:
        job = self._jobs.get(job_id)
        return deepcopy(job) if job else None

    def get_job_by_run(self, experiment_run_id: str) -> ComparisonJobResponse | None:
        job = next(
            (
                candidate
                for candidate in self._jobs.values()
                if candidate.experiment_run_id == experiment_run_id
            ),
            None,
        )
        return deepcopy(job) if job else None

    def run_job(self, job_id: str, request: ComparisonCreateRequest) -> None:
        existing = self._jobs.get(job_id)
        if existing is None:
            return
        experiment_run_id = existing.experiment_run_id
        try:
            result = self.run_comparison(
                request,
                experiment_run_id=experiment_run_id,
                progress_hook=lambda progress: self._set_running(job_id, progress),
            )
            self._jobs[job_id] = ComparisonJobResponse(
                job_id=job_id,
                experiment_run_id=experiment_run_id,
                status="completed",
                progress=ComparisonProgress(
                    total_units=len(result.rows),
                    completed_units=len([row for row in result.rows if row.status != "skipped"]),
                    skipped_units=len([row for row in result.rows if row.status == "skipped"]),
                ),
                result=result,
                message=None,
            )
        except Exception as exc:
            current = self._jobs.get(job_id)
            progress = current.progress if current else existing.progress
            self._jobs[job_id] = ComparisonJobResponse(
                job_id=job_id,
                experiment_run_id=experiment_run_id,
                status="failed",
                progress=progress,
                result=None,
                message=str(exc),
            )

    def run_comparison(
        self,
        request: ComparisonCreateRequest,
        *,
        experiment_run_id: str | None = None,
        progress_hook=None,
    ) -> BatchComparisonResult:
        self._validate_strategy_ids(request.strategy_ids)
        experiment_run_id = experiment_run_id or self._create_experiment_run(
            request,
            name=f"comparison_direct_{uuid4().hex[:12]}",
        )
        selected_scenario = self._resolve_selected_scenario(request)
        scenarios = self._load_batch_scenarios(request, selected_scenario)

        units, precomputed_rows, predictions = self._prepare_units(
            request,
            scenarios,
            experiment_run_id,
        )
        skipped_count = len([row for row in precomputed_rows if row.status == "skipped"])
        precompleted_count = len(precomputed_rows) - skipped_count
        progress = ComparisonProgress(
            total_units=len(units) + len(precomputed_rows),
            completed_units=precompleted_count,
            skipped_units=skipped_count,
        )
        if progress_hook:
            progress_hook(progress)

        rows = [*precomputed_rows]
        completed = precompleted_count
        for unit in units:
            if progress_hook:
                progress_hook(
                    ComparisonProgress(
                        total_units=progress.total_units,
                        completed_units=completed,
                        skipped_units=progress.skipped_units,
                        current_question_id=unit.scenario.question_id,
                        current_strategy_id=unit.strategy_id,
                        current_foil=unit.foil,
                    )
                )
            rows.append(self._run_unit(request, unit, experiment_run_id))
            completed += 1

        selected_comparison = None
        if selected_scenario is not None:
            selected_prediction = predictions.get(selected_scenario.question_id)
            selected_rows = [
                row for row in rows if row.question_id == selected_scenario.question_id
            ]
            selected_comparison = SelectedScenarioComparison(
                scenario=selected_scenario,
                original_answer=selected_prediction.answer if selected_prediction else None,
                ground_truth=selected_scenario.label,
                foils=_unique_letters([row.foil for row in selected_rows if row.foil]),
                rows=selected_rows,
            )

        coverage = self._coverage(request, scenarios, rows)
        return BatchComparisonResult(
            experiment_run_id=experiment_run_id,
            coverage=coverage,
            selected_scenario=selected_comparison,
            summary=self._summarise(rows, request.strategy_ids),
            rows=rows,
        )

    def _set_running(self, job_id: str, progress: ComparisonProgress) -> None:
        existing = self._jobs[job_id]
        self._jobs[job_id] = ComparisonJobResponse(
            job_id=job_id,
            experiment_run_id=existing.experiment_run_id,
            status="running",
            progress=progress,
            result=None,
            message="running comparison",
        )

    def _create_experiment_run(
        self,
        request: ComparisonCreateRequest,
        *,
        name: str,
    ) -> str:
        settings = get_settings()
        record = self._experiment_run_repository.create(
            name=name,
            scenario_subset_id=_scenario_subset_id(request),
            model=request.model,
            budget=request.budget,
            prompt_template_version=settings.target_prompt_version,
            strategy_ids=request.strategy_ids,
            task_type=request.task_type,
            dimension=request.dimension,
            notes=json.dumps(
                {
                    "foil_mode": request.foil_mode,
                    "limit": request.limit,
                    "offset": request.offset,
                },
                sort_keys=True,
            ),
        )
        return record.id

    @staticmethod
    def _validate_strategy_ids(strategy_ids: list[str]) -> None:
        for strategy_id in strategy_ids:
            try:
                get_strategy(strategy_id)
            except KeyError as exc:
                raise ValueError(f"Unknown strategy_id: {strategy_id}") from exc

    def _resolve_selected_scenario(self, request: ComparisonCreateRequest) -> ScenarioItem | None:
        if request.selected_scenario is not None:
            return request.selected_scenario
        if request.selected_question_id is None:
            return None
        found = self._find_scenario(
            request.selected_question_id,
            task_type=request.task_type,
            dimension=request.dimension,
        )
        if found is None:
            raise ValueError(f"Unknown selected_question_id: {request.selected_question_id}")
        return found

    def _load_batch_scenarios(
        self,
        request: ComparisonCreateRequest,
        selected_scenario: ScenarioItem | None,
    ) -> list[ScenarioItem]:
        if request.question_ids:
            all_scenarios = self._load_all_scenarios(
                task_type=request.task_type,
                dimension=request.dimension,
            )
            by_id = {scenario.question_id: scenario for scenario in all_scenarios}
            scenarios = [
                by_id[question_id]
                for question_id in request.question_ids
                if question_id in by_id
            ]
        else:
            scenarios = self._scenario_source.list_scenarios(
                task_type=request.task_type,
                dimension=request.dimension,
                limit=request.limit,
                offset=request.offset,
            ).items

        if selected_scenario is None:
            return scenarios
        return self._include_selected_scenario(scenarios, selected_scenario, request.limit)

    def _include_selected_scenario(
        self,
        scenarios: list[ScenarioItem],
        selected_scenario: ScenarioItem,
        limit: int,
    ) -> list[ScenarioItem]:
        replaced = False
        merged: list[ScenarioItem] = []
        for scenario in scenarios:
            if scenario.question_id == selected_scenario.question_id:
                merged.append(selected_scenario)
                replaced = True
            else:
                merged.append(scenario)

        if not replaced:
            merged.insert(0, selected_scenario)
            if len(merged) > limit:
                merged = merged[:limit]
        return merged

    def _prepare_units(
        self,
        request: ComparisonCreateRequest,
        scenarios: list[ScenarioItem],
        experiment_run_id: str,
    ) -> tuple[list[ComparisonUnit], list[ComparisonRow], dict[str, PredictionResult]]:
        units: list[ComparisonUnit] = []
        precomputed_rows: list[ComparisonRow] = []
        predictions: dict[str, PredictionResult] = {}

        for scenario in scenarios:
            try:
                prediction = self._prediction_service.target_predict(
                    scenario=scenario.scenario,
                    choices=scenario.choices,
                    model=request.model,
                )
            except Exception as exc:
                precomputed_rows.extend(
                    self._prediction_failure_rows(
                        scenario=scenario,
                        request=request,
                        experiment_run_id=experiment_run_id,
                        message=f"original prediction failed: {exc}",
                    )
                )
                continue
            predictions[scenario.question_id] = prediction

            foils = self._foil_plan(scenario, prediction, request.foil_mode)
            if not prediction.answer or not foils:
                precomputed_rows.extend(
                    self._skipped_rows(
                        scenario=scenario,
                        prediction=prediction,
                        request=request,
                        experiment_run_id=experiment_run_id,
                    )
                )
                continue

            for strategy_id in request.strategy_ids:
                for foil in foils:
                    units.append(
                        ComparisonUnit(
                            scenario=scenario,
                            prediction=prediction,
                            strategy_id=strategy_id,
                            foil=foil,
                        )
                    )
        return units, precomputed_rows, predictions

    def _run_unit(
        self,
        request: ComparisonCreateRequest,
        unit: ComparisonUnit,
        experiment_run_id: str,
    ) -> ComparisonRow:
        original_answer = unit.prediction.answer
        if original_answer is None:
            return self._failed_row(
                scenario=unit.scenario,
                prediction=unit.prediction,
                request=request,
                experiment_run_id=experiment_run_id,
                strategy_id=unit.strategy_id,
                foil=unit.foil,
                original_answer=None,
                message="original prediction did not return an answer",
            )

        try:
            payload = self._counterfactual_service.run_once(
                CounterfactualCreateRequest(
                    question_id=unit.scenario.question_id,
                    experiment_run_id=experiment_run_id,
                    scenario=unit.scenario.scenario,
                    choices=unit.scenario.choices,
                    model=request.model,
                    original_answer=original_answer,
                    foil=unit.foil,
                    strategy_id=unit.strategy_id,
                    budget=request.budget,
                )
            )
        except Exception as exc:
            return self._failed_row(
                scenario=unit.scenario,
                prediction=unit.prediction,
                request=request,
                experiment_run_id=experiment_run_id,
                strategy_id=unit.strategy_id,
                foil=unit.foil,
                original_answer=original_answer,
                message=str(exc),
            )
        return self._row_from_payload(
            unit.scenario,
            request.model,
            unit.prediction,
            payload,
            experiment_run_id,
        )

    def _foil_plan(
        self,
        scenario: ScenarioItem,
        prediction: PredictionResult,
        foil_mode: FoilMode,
    ) -> list[ChoiceLetter]:
        if prediction.answer is None:
            return []

        letters = ordered_choice_letters(scenario.choices)
        if foil_mode == "all_non_original":
            return [letter for letter in letters if letter != prediction.answer]

        foil = self._single_foil(scenario, prediction, letters)
        return [foil] if foil else []

    def _single_foil(
        self,
        scenario: ScenarioItem,
        prediction: PredictionResult,
        letters: list[ChoiceLetter],
    ) -> ChoiceLetter | None:
        if scenario.label and scenario.label != prediction.answer:
            return scenario.label

        scored_candidates = [
            (letter, score)
            for letter, score in prediction.option_logprobs.items()
            if letter != prediction.answer and score is not None
        ]
        if scored_candidates:
            return max(scored_candidates, key=lambda item: item[1])[0]

        return next((letter for letter in letters if letter != prediction.answer), None)

    def _skipped_rows(
        self,
        *,
        scenario: ScenarioItem,
        prediction: PredictionResult,
        request: ComparisonCreateRequest,
        experiment_run_id: str,
    ) -> list[ComparisonRow]:
        return [
            ComparisonRow(
                experiment_run_id=experiment_run_id,
                question_id=scenario.question_id,
                scenario_item_id=scenario.scenario_item_id,
                task_type=scenario.task_type,
                dimension=scenario.dimension,
                model=request.model,
                strategy_id=strategy_id,
                original_answer=prediction.answer,
                foil=None,
                ground_truth=scenario.label,
                status="skipped",
                new_answer=None,
                flip_success=False,
                token_edit_distance=None,
                changed_word_fraction=None,
                search_calls=0,
                postprocess_calls=0,
                proposer_calls=0,
                total_target_calls=0,
                runtime_seconds=prediction.runtime_seconds,
                original_logprobs=prediction.option_logprobs,
                modified_scenario=None,
                message="original prediction did not produce a valid answer or foil",
                result=None,
            )
            for strategy_id in request.strategy_ids
        ]

    def _prediction_failure_rows(
        self,
        *,
        scenario: ScenarioItem,
        request: ComparisonCreateRequest,
        experiment_run_id: str,
        message: str,
    ) -> list[ComparisonRow]:
        return [
            self._failed_row(
                scenario=scenario,
                prediction=None,
                request=request,
                experiment_run_id=experiment_run_id,
                strategy_id=strategy_id,
                foil=None,
                original_answer=None,
                message=message,
            )
            for strategy_id in request.strategy_ids
        ]

    def _failed_row(
        self,
        *,
        scenario: ScenarioItem,
        prediction: PredictionResult | None,
        request: ComparisonCreateRequest,
        experiment_run_id: str,
        strategy_id: str,
        foil: ChoiceLetter | None,
        original_answer: ChoiceLetter | None,
        message: str,
    ) -> ComparisonRow:
        return ComparisonRow(
            experiment_run_id=experiment_run_id,
            question_id=scenario.question_id,
            scenario_item_id=scenario.scenario_item_id,
            task_type=scenario.task_type,
            dimension=scenario.dimension,
            model=request.model,
            strategy_id=strategy_id,
            original_answer=original_answer,
            foil=foil,
            ground_truth=scenario.label,
            status="failed",
            new_answer=None,
            flip_success=False,
            token_edit_distance=None,
            changed_word_fraction=None,
            search_calls=0,
            postprocess_calls=0,
            proposer_calls=0,
            total_target_calls=0,
            runtime_seconds=0,
            original_logprobs=(
                prediction.option_logprobs
                if prediction is not None
                else {letter: None for letter in scenario.choices}
            ),
            modified_scenario=None,
            message=message,
            result=None,
        )

    def _row_from_payload(
        self,
        scenario: ScenarioItem,
        model: str,
        prediction: PredictionResult,
        payload: CounterfactualResultPayload,
        experiment_run_id: str,
    ) -> ComparisonRow:
        metrics = payload.metrics
        return ComparisonRow(
            experiment_run_id=payload.experiment_run_id or experiment_run_id,
            question_id=scenario.question_id,
            scenario_item_id=scenario.scenario_item_id,
            task_type=scenario.task_type,
            dimension=scenario.dimension,
            model=model,
            strategy_id=payload.strategy_id,
            original_answer=payload.original_answer,
            foil=payload.foil,
            ground_truth=scenario.label,
            status=payload.status,
            new_answer=payload.new_answer,
            flip_success=metrics.flip_success,
            token_edit_distance=metrics.token_edit_distance,
            changed_word_fraction=metrics.changed_word_fraction,
            search_calls=metrics.search_calls,
            postprocess_calls=metrics.postprocess_calls,
            proposer_calls=metrics.proposer_calls,
            total_target_calls=metrics.total_target_calls,
            runtime_seconds=metrics.runtime_seconds,
            original_logprobs=prediction.option_logprobs,
            foil_logprob_delta=metrics.foil_logprob_delta,
            mean_foil_logprob_delta=metrics.mean_foil_logprob_delta,
            max_foil_logprob_delta=metrics.max_foil_logprob_delta,
            positive_delta_rate=metrics.positive_delta_rate,
            logprob_coverage=metrics.logprob_coverage,
            modified_scenario=payload.modified_scenario,
            message=payload.message,
            result=payload,
        )

    def _coverage(
        self,
        request: ComparisonCreateRequest,
        scenarios: list[ScenarioItem],
        rows: list[ComparisonRow],
    ) -> ComparisonCoverage:
        resolved_ids = {scenario.question_id for scenario in scenarios}
        requested_scenarios = (
            len(request.question_ids) if request.question_ids is not None else request.limit
        )
        missing_question_ids = (
            [
                question_id
                for question_id in request.question_ids
                if question_id not in resolved_ids
            ]
            if request.question_ids is not None
            else []
        )
        completed_units = len([row for row in rows if row.status != "skipped"])
        skipped_units = len(rows) - completed_units
        scenario_coverage_rate = _ratio(len(scenarios), requested_scenarios)
        execution_coverage_rate = _ratio(completed_units, len(rows))
        partial_coverage = (
            len(scenarios) < requested_scenarios
            or bool(missing_question_ids)
            or skipped_units > 0
        )
        return ComparisonCoverage(
            requested_scenarios=requested_scenarios,
            resolved_scenarios=len(scenarios),
            missing_question_ids=missing_question_ids,
            total_units=len(rows),
            completed_units=completed_units,
            skipped_units=skipped_units,
            scenario_coverage_rate=scenario_coverage_rate,
            execution_coverage_rate=execution_coverage_rate,
            partial_coverage=partial_coverage,
        )

    def _summarise(
        self,
        rows: list[ComparisonRow],
        strategy_ids: list[str],
    ) -> list[ComparisonStrategySummary]:
        rows_by_strategy: dict[str, list[ComparisonRow]] = defaultdict(list)
        for row in rows:
            rows_by_strategy[row.strategy_id].append(row)

        summaries: list[ComparisonStrategySummary] = []
        for strategy_id in strategy_ids:
            strategy_rows = rows_by_strategy[strategy_id]
            attempted = [row for row in strategy_rows if row.status != "skipped"]
            successful = [row for row in strategy_rows if row.status == "success"]
            success_count = len(successful)
            not_found_count = len(
                [row for row in strategy_rows if row.status == "not_found"]
            )
            failed_count = len([row for row in strategy_rows if row.status == "failed"])
            skipped_count = len([row for row in strategy_rows if row.status == "skipped"])
            run_count = len(strategy_rows)
            summaries.append(
                ComparisonStrategySummary(
                    strategy_id=strategy_id,
                    runs=run_count,
                    attempted_count=len(attempted),
                    success_count=success_count,
                    not_found_count=not_found_count,
                    failed_count=failed_count,
                    skipped_count=skipped_count,
                    flip_rate=_ratio(success_count, run_count),
                    coverage_rate=_ratio(len(attempted), run_count),
                    partial_coverage=(len(attempted) < run_count or run_count == 0),
                    avg_token_edit_distance=_avg(
                        [row.token_edit_distance for row in successful]
                    ),
                    median_token_edit_distance=_median(
                        [row.token_edit_distance for row in successful]
                    ),
                    avg_changed_word_fraction=_avg(
                        [row.changed_word_fraction for row in successful]
                    ),
                    avg_total_target_calls=_avg(
                        [row.total_target_calls for row in attempted]
                    ),
                    avg_proposer_calls=_avg([row.proposer_calls for row in attempted]),
                    avg_runtime_seconds=_avg([row.runtime_seconds for row in attempted]),
                    avg_foil_logprob_delta=_avg(
                        [row.foil_logprob_delta for row in attempted]
                    ),
                    avg_mean_foil_logprob_delta=_avg(
                        [row.mean_foil_logprob_delta for row in attempted]
                    ),
                    avg_max_foil_logprob_delta=_avg(
                        [row.max_foil_logprob_delta for row in attempted]
                    ),
                    avg_positive_delta_rate=_avg(
                        [row.positive_delta_rate for row in attempted]
                    ),
                    avg_logprob_coverage=_avg(
                        [row.logprob_coverage for row in attempted]
                    ),
                )
            )
        return summaries

    def _find_scenario(
        self,
        question_id: str,
        *,
        task_type: str | None,
        dimension: str | None,
    ) -> ScenarioItem | None:
        for scenario in self._load_all_scenarios(task_type=task_type, dimension=dimension):
            if scenario.question_id == question_id:
                return scenario
        return None

    def _load_all_scenarios(
        self,
        *,
        task_type: str | None,
        dimension: str | None,
    ) -> list[ScenarioItem]:
        scenarios: list[ScenarioItem] = []
        offset = 0
        while True:
            page = self._scenario_source.list_scenarios(
                task_type=task_type,
                dimension=dimension,
                limit=PAGE_SIZE,
                offset=offset,
            )
            if not page.items:
                break
            scenarios.extend(page.items)
            offset += len(page.items)
            if offset >= page.total:
                break
        return scenarios


def _avg(values: list[int | float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 4)


def _median(values: list[int | float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return round(float(median(clean)), 4)


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _scenario_subset_id(request: ComparisonCreateRequest) -> str:
    selected = request.selected_scenario
    payload = {
        "question_ids": request.question_ids,
        "task_type": request.task_type,
        "dimension": request.dimension,
        "limit": request.limit,
        "offset": request.offset,
        "selected_scenario": (
            {
                "question_id": selected.question_id,
                "scenario": selected.scenario,
                "choices": selected.choices,
            }
            if selected is not None
            else None
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
    return f"subset_{digest}"


def _unique_letters(letters: list[ChoiceLetter]) -> list[ChoiceLetter]:
    seen: set[ChoiceLetter] = set()
    unique: list[ChoiceLetter] = []
    for letter in letters:
        if letter in seen:
            continue
        seen.add(letter)
        unique.append(letter)
    return unique
