from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from app.harness.target_predict import PredictionResult


@dataclass(frozen=True)
class CounterfactualRequest:
    question_id: str | None
    scenario: str
    choices: dict[str, str]
    model: str
    original_answer: str
    foil: str
    budget: int


@dataclass(frozen=True)
class AttemptRecord:
    modified_scenario: str
    prediction: PredictionResult | None
    success: bool
    edit_description: str | None = None


@dataclass(frozen=True)
class CounterfactualResult:
    status: str
    original_scenario: str
    modified_scenario: str | None
    original_answer: str
    new_answer: str | None
    foil: str
    strategy_id: str
    attempts: list[AttemptRecord]
    message: str | None = None


TargetPredictFn = Callable[[str, dict[str, str], str], PredictionResult]


class CounterfactualStrategy(ABC):
    id: str
    name: str

    @abstractmethod
    def generate(
        self,
        request: CounterfactualRequest,
        target_predict: TargetPredictFn,
    ) -> CounterfactualResult:
        raise NotImplementedError
