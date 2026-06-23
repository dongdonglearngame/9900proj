from typing import Literal

from app.schemas.common import APIModel, ChoiceLetter, ChoiceMap, OptionScoreMap
from app.schemas.job import JobPhase, JobStatus
from app.schemas.metrics import CounterfactualMetrics


class StrategyInfo(APIModel):
    id: str
    name: str
    available: bool


class StrategyListResponse(APIModel):
    strategies: list[StrategyInfo]


class CounterfactualCreateRequest(APIModel):
    question_id: str | None = None
    scenario: str
    choices: ChoiceMap
    model: str
    original_answer: ChoiceLetter
    foil: ChoiceLetter
    strategy_id: str
    budget: int = 20


class CounterfactualCreateResponse(APIModel):
    job_id: str
    status: JobStatus


class CounterfactualProgress(APIModel):
    budget: int
    search_calls: int
    postprocess_calls: int
    proposer_calls: int


class PredictionSnapshot(APIModel):
    answer: ChoiceLetter | None
    option_logprobs: OptionScoreMap


class DiffSpan(APIModel):
    type: Literal["insert", "delete", "replace"]
    original: str
    modified: str


class CounterfactualResultPayload(APIModel):
    status: Literal["success", "not_found", "failed"]
    strategy_id: str
    original_answer: ChoiceLetter
    foil: ChoiceLetter
    new_answer: ChoiceLetter | None
    original_scenario: str
    modified_scenario: str | None
    original_prediction: PredictionSnapshot | None = None
    new_prediction: PredictionSnapshot | None = None
    diff: list[DiffSpan]
    metrics: CounterfactualMetrics
    message: str | None = None


class CounterfactualJobResponse(APIModel):
    job_id: str
    status: JobStatus
    phase: JobPhase
    progress: CounterfactualProgress
    result: CounterfactualResultPayload | None
    message: str | None = None
