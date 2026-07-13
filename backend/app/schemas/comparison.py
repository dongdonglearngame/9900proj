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
        return self


class ComparisonCreateResponse(APIModel):
    job_id: str
    status: JobStatus


class ComparisonProgress(APIModel):
    total_units: int
    completed_units: int
    skipped_units: int
    current_question_id: str | None = None
    current_strategy_id: str | None = None
    current_foil: ChoiceLetter | None = None


class ComparisonRow(APIModel):
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
    modified_scenario: str | None = None
    message: str | None = None
    result: CounterfactualResultPayload | None = None


class ComparisonStrategySummary(APIModel):
    strategy_id: str
    runs: int
    success_count: int
    not_found_count: int
    failed_count: int
    skipped_count: int
    flip_rate: float | None
    avg_token_edit_distance: float | None
    median_token_edit_distance: float | None
    avg_changed_word_fraction: float | None
    avg_total_target_calls: float | None
    avg_proposer_calls: float | None
    avg_runtime_seconds: float | None


class SelectedScenarioComparison(APIModel):
    scenario: ScenarioItem
    original_answer: ChoiceLetter | None
    ground_truth: ChoiceLetter | None
    foils: list[ChoiceLetter]
    rows: list[ComparisonRow]


class BatchComparisonResult(APIModel):
    selected_scenario: SelectedScenarioComparison | None = None
    summary: list[ComparisonStrategySummary]
    rows: list[ComparisonRow]


class ComparisonJobResponse(APIModel):
    job_id: str
    status: JobStatus
    progress: ComparisonProgress
    result: BatchComparisonResult | None = None
    message: str | None = None
