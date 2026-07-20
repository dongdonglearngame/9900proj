from app.strategies._candidate_filters import (
    is_degenerate_foil_leak,
    s2_semantic_risks,
)


def test_foil_guard_rejects_exact_text_introduced_by_edit() -> None:
    original = "The result left Mira uncertain."
    modified = "The result left Mira feeling a sense of relief."

    assert is_degenerate_foil_leak(original, modified, "relief")


def test_foil_guard_rejects_regular_and_irregular_emotion_derivations() -> None:
    assert is_degenerate_foil_leak(
        "The news changed her mood.",
        "The news left her relieved.",
        "relief",
    )
    assert is_degenerate_foil_leak(
        "The news changed her mood.",
        "The news left her angry.",
        "anger",
    )
    assert is_degenerate_foil_leak(
        "He finally saw the bird.",
        "He finally saw the bird and was delighted.",
        "delight",
    )
    assert is_degenerate_foil_leak(
        "He finally saw the bird.",
        "He finally saw the bird and was thrilled.",
        "delight",
    )


def test_foil_guard_checks_only_the_actual_edit_for_existing_foil_words() -> None:
    original = "She already mentioned relief before the meeting at night."
    modified = "She already mentioned relief before the meeting at noon."

    assert not is_degenerate_foil_leak(original, modified, "relief")


def test_foil_guard_allows_shared_content_words_in_sentence_foils() -> None:
    cases = [
        (
            "He had not decided how to spend the evening.",
            "He joined his friend's group for dinner.",
            "His friend invited him to dinner and he felt nervous.",
        ),
        (
            "Sam listened quietly as Lee described the problem.",
            "Sam offered to help Lee find a counsellor.",
            "Lee should seek professional help immediately.",
        ),
        (
            "Sam listened quietly as Lee described the problem.",
            "Sam offered to help Lee find a counsellor.",
            "Seek professional help.",
        ),
        (
            "The appointment remained on the calendar for Monday.",
            "The meetings were rescheduled for Tuesday.",
            "The meeting was cancelled because nobody could attend.",
        ),
    ]

    assert all(
        not is_degenerate_foil_leak(original, modified, foil)
        for original, modified, foil in cases
    )


def test_foil_guard_does_not_claim_to_detect_semantic_leakage() -> None:
    original = "The alarm was still active."
    modified = "The danger had passed."

    assert not is_degenerate_foil_leak(original, modified, "relief")


def test_s2_semantic_risks_flag_evaluative_cue_only_edits() -> None:
    assert s2_semantic_risks(
        "Ricky lost the match.",
        "Ricky surprisingly lost the match.",
    ) == ("evaluative_cue_only",)
    assert s2_semantic_risks(
        "The service was rude.",
        "The service was unique.",
    ) == ("evaluative_cue_only",)


def test_s2_semantic_risks_flag_known_near_synonym_behaviour_swap() -> None:
    assert s2_semantic_risks(
        "Mina was frowning at the result.",
        "Mina was scowling at the result.",
    ) == ("near_synonym_only",)


def test_s2_semantic_risks_flag_removed_token_referenced_later() -> None:
    assert s2_semantic_risks(
        "Omar won the race. He raised the race trophy.",
        "Omar reached the final. He raised the race trophy.",
    ) == ("downstream_reference",)


def test_s2_semantic_risks_do_not_block_event_outcome_edit() -> None:
    assert not s2_semantic_risks(
        "Leah's application was rejected.",
        "Leah's application was approved.",
    )


def test_s2_semantic_risks_do_not_treat_ly_suffix_as_an_adverb() -> None:
    assert not s2_semantic_risks(
        "Noah met the group.",
        "Noah met the family.",
    )
