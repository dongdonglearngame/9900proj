import importlib
import inspect
import pkgutil
from functools import lru_cache

from app.schemas.counterfactual import StrategyInfo
from app.strategies.base import CounterfactualStrategy

_SKIP_MODULES = {"base", "registry"}

PLANNED_STRATEGIES = [
    StrategyInfo(id="s2_llm_propose_verify", name="S2 LLM Propose-Verify", available=False),
    StrategyInfo(
        id="s4_importance_infilling",
        name="S4 Importance-guided Infilling",
        available=False,
    ),
]


def get_strategy(strategy_id: str) -> CounterfactualStrategy:
    strategies = _available_strategies()
    if strategy_id not in strategies:
        raise KeyError(f"Unknown strategy {strategy_id}")
    return strategies[strategy_id]


def list_strategy_infos() -> list[StrategyInfo]:
    available = [
        StrategyInfo(id=strategy.id, name=strategy.name, available=True)
        for strategy in _available_strategies().values()
    ]
    return [*available, *PLANNED_STRATEGIES]


@lru_cache
def _available_strategies() -> dict[str, CounterfactualStrategy]:
    _import_strategy_modules()
    strategies: dict[str, CounterfactualStrategy] = {}

    for strategy_class in _iter_strategy_classes(CounterfactualStrategy):
        strategy = strategy_class()
        if strategy.id in strategies:
            raise ValueError(f"Duplicate counterfactual strategy id: {strategy.id}")
        strategies[strategy.id] = strategy

    return strategies


def _import_strategy_modules() -> None:
    package = importlib.import_module("app.strategies")
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.name in _SKIP_MODULES or module_info.name.startswith("_"):
            continue
        importlib.import_module(f"{package.__name__}.{module_info.name}")


def _iter_strategy_classes(
    strategy_class: type[CounterfactualStrategy],
) -> list[type[CounterfactualStrategy]]:
    classes: list[type[CounterfactualStrategy]] = []

    for subclass in strategy_class.__subclasses__():
        classes.extend(_iter_strategy_classes(subclass))
        if not inspect.isabstract(subclass):
            classes.append(subclass)

    return classes
