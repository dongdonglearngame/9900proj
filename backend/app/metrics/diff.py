from difflib import SequenceMatcher

from app.schemas.counterfactual import DiffSpan


def word_diff(original: str, modified: str | None) -> list[DiffSpan]:
    if modified is None:
        return []
    original_words = original.split()
    modified_words = modified.split()
    matcher = SequenceMatcher(a=original_words, b=modified_words)
    spans: list[DiffSpan] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        span_type = "replace" if tag == "replace" else tag
        spans.append(
            DiffSpan(
                type=span_type,
                original=" ".join(original_words[i1:i2]),
                modified=" ".join(modified_words[j1:j2]),
            )
        )
    return spans
