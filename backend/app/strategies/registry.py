from app.schemas.counterfactual import StrategyInfo
from app.strategies.base import CounterfactualStrategy
from app.strategies.s1_word_greedy import S1WordGreedyStrategy

STRATEGIES: dict[str, CounterfactualStrategy] = {
    "s1_word_greedy": S1WordGreedyStrategy(),
}

PLANNED_STRATEGIES = [
    StrategyInfo(id="s2_llm_propose_verify", name="S2 LLM Propose-Verify", available=False),
    StrategyInfo(
        id="s4_importance_infilling",
        name="S4 Importance-guided Infilling",
        available=False,
    ),
]


def get_strategy(strategy_id: str) -> CounterfactualStrategy:
    if strategy_id not in STRATEGIES:
        raise KeyError(f"Unknown strategy {strategy_id}")
    return STRATEGIES[strategy_id]


def list_strategy_infos() -> list[StrategyInfo]:
    available = [
        StrategyInfo(id=strategy.id, name=strategy.name, available=True)
        for strategy in STRATEGIES.values()
    ]
    return [*available, *PLANNED_STRATEGIES]
