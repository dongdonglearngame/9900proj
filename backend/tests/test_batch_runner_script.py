import argparse

import pytest

from app.scripts.batch_run_counterfactuals import _strategy_ids


def test_strategy_ids_parse_comma_separated_values() -> None:
    assert _strategy_ids("s1_word_greedy, s2_llm_propose_verify") == [
        "s1_word_greedy",
        "s2_llm_propose_verify",
    ]


def test_strategy_ids_reject_duplicates() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="must not contain duplicates"):
        _strategy_ids("s1_word_greedy,s1_word_greedy")
