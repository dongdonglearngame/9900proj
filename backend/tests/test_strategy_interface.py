from inspect import signature

from app.llm.mock_client import MockLLMClient
from app.strategies.base import (
    CounterfactualResult,
    CounterfactualStrategy,
    FrozenTargetModel,
    Proposer,
)
from app.strategies.registry import get_strategy, list_strategy_infos

CHOICES = {
    "A": "Ignore the texts and continue sleeping",
    "B": "Tell her friend to seek professional help",
    "C": "Stay up and lend a listening ear",
    "D": "Suggest her friend find a new partner",
}


def test_strategy_interface_signature_matches_shared_contract() -> None:
    generate_signature = signature(CounterfactualStrategy.generate)

    assert list(generate_signature.parameters) == [
        "self",
        "scenario",
        "choices",
        "model",
        "foil",
        "budget",
        "proposer",
    ]
    assert generate_signature.return_annotation is CounterfactualResult
    assert generate_signature.parameters["proposer"].annotation is Proposer


def test_frozen_target_model_only_exposes_target_predict() -> None:
    calls: list[str] = []

    def target_predict(scenario: str, choices: dict[str, str], model: str):
        calls.append(model)
        return MockLLMClient().predict(scenario=scenario, choices=choices, model=model)

    model = FrozenTargetModel(model_id="mock", target_predict_fn=target_predict)

    assert [name for name in dir(model) if not name.startswith("_")] == ["target_predict"]
    assert not hasattr(model, "predict")
    assert not hasattr(model, "client")

    prediction = model.target_predict("A calm afternoon check-in.", CHOICES)

    assert calls == ["mock"]
    assert prediction.model == "mock"


def test_registry_lists_s1() -> None:
    strategies = list_strategy_infos()
    assert any(strategy.id == "s1_word_greedy" and strategy.available for strategy in strategies)


def test_registry_lists_s2_once_as_available() -> None:
    strategies = list_strategy_infos()
    s2_entries = [strategy for strategy in strategies if strategy.id == "s2_llm_propose_verify"]

    assert len(s2_entries) == 1
    assert s2_entries[0].available


def test_registry_lists_s6_once_as_available() -> None:
    strategies = list_strategy_infos()
    s6_entries = [strategy for strategy in strategies if strategy.id == "s6_concept_causal_editing"]

    assert len(s6_entries) == 1
    assert s6_entries[0].available


def test_registry_lists_s4_once_as_available() -> None:
    strategies = list_strategy_infos()
    s4_entries = [strategy for strategy in strategies if strategy.id == "s4_importance_infilling"]

    assert len(s4_entries) == 1
    assert s4_entries[0].available


def test_registry_gets_s1() -> None:
    strategy = get_strategy("s1_word_greedy")

    assert isinstance(strategy, CounterfactualStrategy)
    assert strategy.name == "S1 Word-level Greedy"
