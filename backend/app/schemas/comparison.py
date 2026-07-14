from typing import Literal

from pydantic import Field, model_validator

from app.schemas.common import APIModel, ChoiceLetter, OptionScoreMap
from app.schemas.counterfactual import CounterfactualResultPayload
from app.schemas.job import JobStatus
from app.schemas.scenario import ScenarioItem

FoilMode = Literal["single", "all_non_original"]


class ComparisonCreateRequest(APIModel):
    model: str
    strategy_ids: list[str]
    selected_scenario: ScenarioItem | None = None
    selected_question_id: str | None = None
    task_type: str | None = None
    dimension: str | None = None
    question_ids: list[str] | None = None
    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    budget: int = Field(default=20, ge=1, le=100)
    foil_mode: FoilMode = "single"

    @model_validator(mode="after")
    def validate_request(self) -> "ComparisonCreateRequest":
        if not self.strategy_ids:
            raise ValueError("strategy_ids must contain at least one strategy")
        if len(set(self.strategy_ids)) != len(self.strategy_ids):
            raise ValueError("strategy_ids must not contain duplicates")
        if self.question_ids is not None:
            if not self.question_ids:
                raise ValueError("question_ids must be omitted or contain at least one ID")
            if len(set(self.question_ids)) != len(self.question_ids):
                raise ValueError("question_ids must not contain duplicates")
        if (
            self.selected_scenario is not None
            and self.selected_question_id is not None
            and self.selected_scenario.question_id != self.selected_question_id
        ):
            raise ValueError("selected_question_id must match selected_scenario.question_id")
        selected_id = (
            self.selected_scenario.question_id
            if self.selected_scenario is not None
            else self.selected_question_id
        )
        if (
            self.question_ids is not None
            and selected_id is not None
            and selected_id not in self.question_ids
        ):
            raise ValueError("question_ids must include the selected scenario")
        return self


class ComparisonCreateResponse(APIModel):
    job_id: str
    experiment_run_id: str
    status: JobStatus


class ComparisonProgress(APIModel):
    total_units: int
    completed_units: int
    skipped_units: int
    current_question_id: str | None = None
    current_strategy_id: str | None = None
    current_foil: ChoiceLetter | None = None


class ComparisonRow(APIModel):
    experiment_run_id: str
    question_id: str
    scenario_item_id: str
    task_type: str
    dimension: str
    model: str
    strategy_id: str
    original_answer: ChoiceLetter | None
    foil: ChoiceLetter | None
    ground_truth: ChoiceLetter | None
    status: Literal["success", "not_found", "failed", "skipped"]
    new_answer: ChoiceLetter | None
    flip_success: bool
    token_edit_distance: int | None
    changed_word_fraction: float | None
    search_calls: int
    postprocess_calls: int
    proposer_calls: int
    total_target_calls: int
    runtime_seconds: float
    original_logprobs: OptionScoreMap
    foil_logprob_delta: float | None = None
    mean_foil_logprob_delta: float | None = None
    max_foil_logprob_delta: float | None = None
    positive_delta_rate: float | None = None
    logprob_coverage: float | None = None
    modified_scenario: str | None = None
    message: str | None = None
    result: CounterfactualResultPayload | None = None


class ComparisonStrategySummary(APIModel):
    strategy_id: str
    runs: int
    attempted_count: int
    success_count: int
    not_found_count: int
    failed_count: int
    skipped_count: int
    flip_rate: float | None
    coverage_rate: float | None
    partial_coverage: bool
    avg_token_edit_distance: float | None
    median_token_edit_distance: float | None
    avg_changed_word_fraction: float | None
    avg_total_target_calls: float | None
    avg_proposer_calls: float | None
    avg_runtime_seconds: float | None
    avg_foil_logprob_delta: float | None = None
    avg_mean_foil_logprob_delta: float | None = None
    avg_max_foil_logprob_delta: float | None = None
    avg_positive_delta_rate: float | None = None
    avg_logprob_coverage: float | None = None


class SelectedScenarioComparison(APIModel):
    scenario: ScenarioItem
    original_answer: ChoiceLetter | None
    ground_truth: ChoiceLetter | None
    foils: list[ChoiceLetter]
    rows: list[ComparisonRow]


class ComparisonCoverage(APIModel):
    requested_scenarios: int
    resolved_scenarios: int
    missing_question_ids: list[str]
    total_units: int
    completed_units: int
    skipped_units: int
    scenario_coverage_rate: float | None
    execution_coverage_rate: float | None
    partial_coverage: bool


class BatchComparisonResult(APIModel):
    experiment_run_id: str
    coverage: ComparisonCoverage
    selected_scenario: SelectedScenarioComparison | None = None
    summary: list[ComparisonStrategySummary]
    rows: list[ComparisonRow]


class ComparisonJobResponse(APIModel):
    job_id: str
    experiment_run_id: str
    status: JobStatus
    progress: ComparisonProgress
    result: BatchComparisonResult | None = None
    message: str | None = None
