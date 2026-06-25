from app.harness.parser import parse_answer_letter


def test_parse_answer_letter_accepts_single_choice_formats() -> None:
    assert parse_answer_letter("A") == "A"
    assert parse_answer_letter("b.") == "B"
    assert parse_answer_letter("Answer: c") == "C"
    assert parse_answer_letter("final answer is D") == "D"
    assert parse_answer_letter("Choice - a") == "A"
    assert parse_answer_letter("The answer is C") == "C"
    assert parse_answer_letter("The correct answer is d") == "D"


def test_parse_answer_letter_rejects_unconstrained_text() -> None:
    assert parse_answer_letter("not sure") is None
    assert parse_answer_letter("this is a plausible answer, but c is better") is None
    assert parse_answer_letter("I choose C because she needs support") is None
