import re
from functools import lru_cache

from app.schemas.common import ChoiceMap, ordered_choice_letters


@lru_cache
def _compiled_patterns(letters: tuple[str, ...]) -> tuple[re.Pattern[str], re.Pattern[str]]:
    letter_class = "".join(re.escape(letter) for letter in letters)
    clean_letter_re = re.compile(rf"^\s*([{letter_class}])\s*[\.\)]?\s*$", re.IGNORECASE)
    answer_prefix_re = re.compile(
        r"^\s*(?:answer|final answer|choice|the answer|the correct answer)"
        rf"\s*(?:is|:|-)?\s*([{letter_class}])\s*[\.\)]?\s*$",
        re.IGNORECASE,
    )
    return clean_letter_re, answer_prefix_re


def parse_answer_letter(raw_response: str, choices: ChoiceMap) -> str | None:
    """Parse the model's chosen letter out of its raw response.

    Keep this deliberately constrained: long explanations are treated as parse failures
    so the frozen harness remains a stable multiple-choice function.
    """
    text = raw_response.strip()
    clean_letter_re, answer_prefix_re = _compiled_patterns(tuple(ordered_choice_letters(choices)))
    match = clean_letter_re.fullmatch(text) or answer_prefix_re.fullmatch(text)
    if match is None:
        return None
    return match.group(1).upper()
