from app.metrics.diff import word_diff
from app.metrics.edit_distance import changed_word_fraction, token_edit_distance


def test_word_diff_for_regina_edit() -> None:
    original = "Regina is texting in the middle of the night."
    modified = "Regina is texting in the early evening."
    spans = word_diff(original, modified)
    assert spans[0].type == "replace"
    assert spans[0].original == "middle of the night."
    assert spans[0].modified == "early evening."


def test_token_edit_distance() -> None:
    assert token_edit_distance("a b c", "a x c") == 1
    assert changed_word_fraction("a b c", "a x c") == 0.3333
