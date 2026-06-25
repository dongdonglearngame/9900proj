from app.harness.parser import parse_answer_letter

FOUR_CHOICES = {"A": "a", "B": "b", "C": "c", "D": "d"}
SIX_CHOICES = {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e", "F": "f"}


def test_parse_answer_letter_accepts_single_choice_formats() -> None:
    assert parse_answer_letter("A", FOUR_CHOICES) == "A"
    assert parse_answer_letter("b.", FOUR_CHOICES) == "B"
    assert parse_answer_letter("Answer: c", FOUR_CHOICES) == "C"
    assert parse_answer_letter("final answer is D", FOUR_CHOICES) == "D"
    assert parse_answer_letter("Choice - a", FOUR_CHOICES) == "A"
    assert parse_answer_letter("The answer is C", FOUR_CHOICES) == "C"
    assert parse_answer_letter("The correct answer is d", FOUR_CHOICES) == "D"
    assert parse_answer_letter("Answer: f", SIX_CHOICES) == "F"


def test_parse_answer_letter_rejects_unconstrained_text() -> None:
    assert parse_answer_letter("not sure", FOUR_CHOICES) is None
    assert parse_answer_letter("this is a plausible answer, but c is better", FOUR_CHOICES) is None
    assert parse_answer_letter("I choose C because she needs support", FOUR_CHOICES) is None


def test_parse_answer_letter_rejects_letters_outside_current_choices() -> None:
    assert parse_answer_letter("Answer: F", FOUR_CHOICES) is None
    assert parse_answer_letter("G", SIX_CHOICES) is None
