import argparse

import pytest

from app.scripts.batch_run_counterfactuals import (
    _question_ids,
    _question_ids_file,
    _strategy_ids,
)


def test_strategy_ids_parse_comma_separated_values() -> None:
    assert _strategy_ids("s1_word_greedy, s2_llm_propose_verify") == [
        "s1_word_greedy",
        "s2_llm_propose_verify",
    ]


def test_strategy_ids_reject_duplicates() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="must not contain duplicates"):
        _strategy_ids("s1_word_greedy,s1_word_greedy")


def test_question_ids_parse_fixed_subset_and_reject_duplicates() -> None:
    assert _question_ids("q1, q2") == ["q1", "q2"]
    with pytest.raises(argparse.ArgumentTypeError, match="must not contain duplicates"):
        _question_ids("q1,q1")


def test_question_ids_file_ignores_comments_and_blank_lines(tmp_path) -> None:
    path = tmp_path / "ids.txt"
    path.write_text("# fixed subset\nq1\n\nq2\n", encoding="utf-8")

    assert _question_ids_file(path) == ["q1", "q2"]
