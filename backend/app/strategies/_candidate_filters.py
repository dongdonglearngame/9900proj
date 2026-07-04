import re

from app.metrics.edit_distance import changed_word_fraction

WORD_RE = re.compile(r"[A-Za-z0-9']+")


def normalise_key(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def is_degenerate_foil_leak(
    candidate: str,
    foil_text: str,
    *,
    ngram_size: int = 4,
    overlap_threshold: float = 0.8,
) -> bool:
    candidate_key = normalise_key(candidate)
    foil_key = normalise_key(foil_text)
    if not candidate_key or not foil_key:
        return False
    if foil_key in candidate_key:
        return True

    foil_ngrams = _word_ngrams(foil_key, ngram_size)
    if not foil_ngrams:
        return False

    candidate_ngrams = _word_ngrams(candidate_key, ngram_size)
    if not candidate_ngrams:
        return False

    overlap = len(foil_ngrams & candidate_ngrams) / len(foil_ngrams)
    return overlap >= overlap_threshold


def exceeds_changed_fraction(
    original: str,
    modified: str,
    max_changed_fraction: float,
) -> bool:
    fraction = changed_word_fraction(original, modified)
    return fraction is not None and fraction > max_changed_fraction


def _word_ngrams(value: str, ngram_size: int) -> set[tuple[str, ...]]:
    words = WORD_RE.findall(value)
    if len(words) < ngram_size:
        return set()
    return {
        tuple(words[index : index + ngram_size])
        for index in range(0, len(words) - ngram_size + 1)
    }
