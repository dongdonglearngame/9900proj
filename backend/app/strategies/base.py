from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from app.harness.target_predict import PredictionResult

TargetPredictFn = Callable[[str, dict[str, str], str], PredictionResult]


class TargetModel(Protocol):
    """Frozen target-model harness exposed to counterfactual strategies.

    Strategies receive this object as the `model` argument to `generate`.
    The only supported model access path is `model.target_predict(...)`, which
    runs the shared target harness with the fixed model id selected by the API
    request. Strategies must not import or instantiate LLM clients directly.
    """

    def target_predict(self, scenario: str, choices: dict[str, str]) -> PredictionResult:
        """Run the frozen target prediction harness for one candidate scenario."""


@dataclass(frozen=True)
class ProposedEdit:
    modified_scenario: str
    rationale: str | None = None
    changed_span: str | None = None
    change_type: str | None = None


@dataclass(frozen=True)
class ConceptEdit:
    concept_class: str
    original_span: str
    replacement_span: str
    source_value: str | None = None
    target_value: str | None = None
    rationale: str | None = None


ConceptEditKey = tuple[str, str, str]


class Proposer(Protocol):
    """Generative search-agent port exposed to strategies.

    The proposer may see the foil. It is separate from the frozen target harness and
    must not use the target prediction cache.
    """

    def propose(
        self,
        scenario: str,
        choices: dict[str, str],
        foil: str,
        count: int,
        avoid: list[str] | None = None,
    ) -> list[ProposedEdit]:
        """Generate candidate scenario rewrites for later target verification."""

    def propose_concept_edits(
        self,
        scenario: str,
        choices: dict[str, str],
        foil: str,
        count: int,
        allowed_concepts: tuple[str, ...],
        avoid: list[str] | None = None,
        used_edits: list[ConceptEditKey] | None = None,
    ) -> list[ConceptEdit]:
        """Generate single-concept span replacements for later target verification."""

    def repair_concept_edit(
        self,
        scenario: str,
        choices: dict[str, str],
        foil: str,
        edit: ConceptEdit,
        allowed_concepts: tuple[str, ...],
        used_edits: list[ConceptEditKey] | None = None,
    ) -> ConceptEdit | None:
        """Repair one concept edit's span grounding without changing its intervention."""

    def infill(
        self,
        original_scenario: str,
        masked_scenario: str,
        choices: dict[str, str],
        foil: str,
        count: int,
        avoid: list[str] | None = None,
    ) -> list[ProposedEdit]:
        """Fill masked scenario spans while preserving the unmasked text."""


class FrozenTargetModel:
    """Adapter that hides the raw model client and model id from strategies."""

    __slots__ = ("__model_id", "__target_predict_fn")

    def __init__(self, model_id: str, target_predict_fn: TargetPredictFn) -> None:
        self.__model_id = model_id
        self.__target_predict_fn = target_predict_fn

    def target_predict(self, scenario: str, choices: dict[str, str]) -> PredictionResult:
        return self.__target_predict_fn(scenario, choices, self.__model_id)


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
    new_answer: str | None
    foil: str
    strategy_id: str
    attempts: list[AttemptRecord]
    message: str | None = None
    concept_edit: ConceptEdit | None = None


class CounterfactualStrategy(ABC):
    """Shared interface implemented by every counterfactual strategy.

    `generate` receives only the immutable scenario data, the requested foil, a
    search budget, the frozen target-model harness, and the injected proposer
    harness. This keeps strategies comparable: target prompt templates,
    decoding settings, caching, and model id are owned by the shared harness
    instead of by individual strategy implementations.
    """

    id: str
    name: str

    @abstractmethod
    def generate(
        self,
        scenario: str,
        choices: dict[str, str],
        model: TargetModel,
        foil: str,
        budget: int,
        proposer: Proposer,
    ) -> CounterfactualResult:
        """Search for a candidate scenario that makes the target model choose `foil`."""
        raise NotImplementedError
