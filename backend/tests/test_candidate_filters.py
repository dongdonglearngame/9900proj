from app.strategies._candidate_filters import is_degenerate_foil_leak


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
