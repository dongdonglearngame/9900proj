from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class ScenarioItem(SQLModel, table=True):
    __tablename__ = "scenario_items"

    id: str = Field(primary_key=True)
    source_dataset: str
    source_item_id: str
    scenario_hash: str = Field(index=True)
    scenario_text: str
    subject: str | None = None
    raw_json: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Question(SQLModel, table=True):
    __tablename__ = "questions"

    id: str = Field(primary_key=True)
    scenario_item_id: str = Field(index=True)
    source_question_id: str | None = None
    task_type: str
    dimension: str
    question_text: str | None = None
    choices_json: str
    choices_hash: str = Field(index=True)
    ground_truth: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Prediction(SQLModel, table=True):
    __tablename__ = "predictions"

    id: str = Field(primary_key=True)
    cache_key: str = Field(index=True, unique=True)
    question_id: str | None = Field(default=None, index=True)
    scenario_hash: str = Field(index=True)
    choices_hash: str = Field(index=True)
    model: str
    prompt_template_version: str
    endpoint_type: str
    answer: str | None = None
    status: str
    raw_response: str
    option_logprobs_json: str
    option_probs_json: str
    top_logprobs_raw_json: str
    runtime_seconds: float
    created_at: datetime = Field(default_factory=utc_now)


class CounterfactualJob(SQLModel, table=True):
    __tablename__ = "counterfactual_jobs"

    id: str = Field(primary_key=True)
    status: str = Field(index=True)
    phase: str
    strategy_id: str = Field(index=True)
    model: str
    foil: str
    budget: int
    search_calls: int = 0
    postprocess_calls: int = 0
    proposer_calls: int = 0
    message: str | None = None
    error_message: str | None = None
    result_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Counterfactual(SQLModel, table=True):
    __tablename__ = "counterfactuals"

    id: str = Field(primary_key=True)
    job_id: str = Field(index=True)
    question_id: str | None = Field(default=None, index=True)
    strategy_id: str = Field(index=True)
    model: str
    status: str
    original_answer: str
    foil: str
    new_answer: str | None = None
    original_scenario: str
    modified_scenario: str | None = None
    diff_json: str
    attempts_json: str
    original_prediction_json: str | None = None
    new_prediction_json: str | None = None
    message: str | None = None
    runtime_seconds: float
    created_at: datetime = Field(default_factory=utc_now)


class Metric(SQLModel, table=True):
    __tablename__ = "metrics"

    id: str = Field(primary_key=True)
    counterfactual_id: str = Field(index=True)
    strategy_id: str = Field(index=True)
    flip_success: bool
    token_edit_distance: int | None = None
    changed_word_fraction: float | None = None
    perplexity: float | None = None
    fluency_score: float | None = None
    search_calls: int
    postprocess_calls: int
    proposer_calls: int
    total_target_calls: int
    runtime_seconds: float
    created_at: datetime = Field(default_factory=utc_now)
