from app.strategies.registry import get_strategy, list_strategy_infos


def test_registry_lists_s1() -> None:
    strategies = list_strategy_infos()
    assert any(strategy.id == "s1_word_greedy" and strategy.available for strategy in strategies)


def test_registry_gets_s1() -> None:
    assert get_strategy("s1_word_greedy").name == "S1 Word-level Greedy"
