import re
from difflib import SequenceMatcher

from app.metrics.diff import word_diff
from app.metrics.edit_distance import changed_word_fraction, token_edit_distance

WORD_RE = re.compile(r"[A-Za-z0-9']+")
SENTENCE_BOUNDARY_RE = re.compile(
    r"(?:(?<=[.!?])|(?<=[.!?][\"'\u201d\u2019)\]]))\s+|[\r\n]+"
)
MORPH_STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "for",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "up",
    "with",
}
S2_ANCHOR_STOPWORDS = MORPH_STOPWORDS | {
    "after",
    "before",
    "he",
    "her",
    "hers",
    "him",
    "his",
    "i",
    "it",
    "its",
    "me",
    "my",
    "our",
    "ours",
    "she",
    "that",
    "their",
    "theirs",
    "them",
    "then",
    "they",
    "this",
    "those",
    "today",
    "tomorrow",
    "we",
    "when",
    "while",
    "yesterday",
    "you",
    "your",
}

EMOTION_DERIVATION_FAMILIES = (
    frozenset({"admiration", "admirable", "admiring"}),
    frozenset({"anticipation", "anticipating", "anticipated"}),
    frozenset({"relief", "relieved", "relieving"}),
    frozenset({"anger", "angry", "angrily"}),
    frozenset({"annoyance", "annoyed", "annoying"}),
    frozenset({"boredom", "bored", "boring"}),
    frozenset({"confusion", "confused", "confusing"}),
    frozenset({"delight", "delighted", "delightful", "thrill", "thrilled", "thrilling"}),
    frozenset({"disapproval", "disapproving"}),
    frozenset({"disgust", "disgusted", "disgusting"}),
    frozenset({"guilt", "guilty"}),
    frozenset({"pride", "proud", "proudly"}),
    frozenset({"fear", "afraid", "fearful"}),
    frozenset({"embarrassment", "embarrassed", "embarrassing"}),
    frozenset({"happiness", "happy"}),
    frozenset({"hope", "hopeful", "hopeless", "hopelessness"}),
    frozenset({"joy", "joyful", "joyous"}),
    frozenset({"sadness", "sad"}),
    frozenset({"anxiety", "anxious"}),
    frozenset({"gratitude", "grateful"}),
    frozenset({"jealousy", "jealous"}),
    frozenset({"loneliness", "lonely"}),
    frozenset({"disappointment", "disappointed"}),
    frozenset({"excitement", "excited"}),
    frozenset({"surprise", "surprised"}),
    frozenset({"shame", "ashamed"}),
    frozenset({"worry", "worried"}),
    frozenset({"nervousness", "nervous"}),
    frozenset({"optimism", "optimistic"}),
    frozenset({"pessimism", "pessimistic"}),
    frozenset({"remorse", "remorseful"}),
    frozenset({"trust", "trusting", "trustful"}),
)

_EMOTION_FAMILY_BY_WORD = {
    word: family
    for family in EMOTION_DERIVATION_FAMILIES
    for word in family
}


def normalise_key(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def is_degenerate_foil_leak(
    original: str,
    candidate: str,
    foil_text: str,
    *,
    ngram_size: int = 4,
    overlap_threshold: float = 0.8,
) -> bool:
    """Reject foil wording introduced by the edit, including clear derivations.

    Only inserted and replaced text is inspected for token-level leakage. This avoids
    rejecting an unrelated edit when the original scenario already contained a foil word.
    """

    candidate_key = normalise_key(candidate)
    original_key = normalise_key(original)
    foil_key = normalise_key(foil_text)
    if not candidate_key or not foil_key:
        return False
    if foil_key in candidate_key and foil_key not in original_key:
        return True

    changed_text = " ".join(
        span.modified
        for span in word_diff(original, candidate)
        if span.type in {"insert", "replace"} and span.modified
    )
    changed_key = normalise_key(changed_text)
    if not changed_key:
        return False
    if foil_key in changed_key:
        return True

    changed_words = WORD_RE.findall(changed_key)
    foil_words = WORD_RE.findall(foil_key)
    foil_content_words = [word for word in foil_words if word not in MORPH_STOPWORDS]
    allow_generic_morphology = (
        0 < len(foil_content_words) <= 3
        and any(word in _EMOTION_FAMILY_BY_WORD for word in foil_content_words)
    )
    if any(
        _morphologically_related(
            changed_word,
            foil_word,
            allow_generic=allow_generic_morphology,
        )
        for changed_word in changed_words
        for foil_word in foil_words
    ):
        return True

    foil_ngrams = _word_ngrams(foil_key, ngram_size)
    if not foil_ngrams:
        return False

    changed_ngrams = _word_ngrams(changed_key, ngram_size)
    if not changed_ngrams:
        return False

    overlap = len(foil_ngrams & changed_ngrams) / len(foil_ngrams)
    return overlap >= overlap_threshold


def exceeds_changed_fraction(
    original: str,
    modified: str,
    max_changed_fraction: float,
) -> bool:
    fraction = changed_word_fraction(original, modified)
    return fraction is not None and fraction > max_changed_fraction


def changed_word_count(original: str, modified: str) -> int:
    """Return the same word-level edit count exposed in result metrics."""

    return token_edit_distance(original, modified) or 0


def s2_edit_constraint_violation(
    original: str,
    modified: str,
    *,
    max_changed_words: int,
    require_single_existing_sentence: bool = True,
) -> str | None:
    """Return the first deterministic S2 quality constraint that is violated."""

    if require_single_existing_sentence:
        changed_pair = _changed_sentence_pair(original, modified)
        if changed_pair is None:
            return "sentence_structure"
        if not _shares_sentence_anchor(*changed_pair):
            return "sentence_anchor"
    if changed_word_count(original, modified) > max_changed_words:
        return "changed_word_limit"
    return None


def _changed_sentence_pair(original: str, modified: str) -> tuple[str, str] | None:
    original_sentences = _sentences(original)
    modified_sentences = _sentences(modified)
    if not original_sentences or len(original_sentences) != len(modified_sentences):
        return None

    changed_pairs = [
        (left, right)
        for left, right in zip(original_sentences, modified_sentences, strict=True)
        if normalise_key(left) != normalise_key(right)
    ]
    return changed_pairs[0] if len(changed_pairs) == 1 else None


def _shares_sentence_anchor(original_sentence: str, modified_sentence: str) -> bool:
    original_words = {
        word
        for word in WORD_RE.findall(original_sentence.casefold())
        if word not in S2_ANCHOR_STOPWORDS
    }
    modified_words = {
        word
        for word in WORD_RE.findall(modified_sentence.casefold())
        if word not in S2_ANCHOR_STOPWORDS
    }
    return bool(original_words & modified_words)


def _sentences(value: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in SENTENCE_BOUNDARY_RE.split(value.strip())
        if sentence.strip()
    ]


def _word_ngrams(value: str, ngram_size: int) -> set[tuple[str, ...]]:
    words = WORD_RE.findall(value)
    if len(words) < ngram_size:
        return set()
    return {
        tuple(words[index : index + ngram_size])
        for index in range(0, len(words) - ngram_size + 1)
    }


def _morphologically_related(
    candidate_word: str,
    foil_word: str,
    *,
    allow_generic: bool,
) -> bool:
    if candidate_word in MORPH_STOPWORDS or foil_word in MORPH_STOPWORDS:
        return False

    candidate_family = _EMOTION_FAMILY_BY_WORD.get(candidate_word)
    foil_family = _EMOTION_FAMILY_BY_WORD.get(foil_word)
    if candidate_family is not None and candidate_family == foil_family:
        return True

    # Long cause/behaviour options naturally share ordinary scenario nouns and verbs.
    # Generic surface similarity is useful only for short label-like foils.
    if not allow_generic:
        return False
    if min(len(candidate_word), len(foil_word)) < 4:
        return False
    if candidate_word == foil_word:
        return True
    common_prefix = 0
    for left, right in zip(candidate_word, foil_word, strict=False):
        if left != right:
            break
        common_prefix += 1
    return (
        common_prefix >= 4
        and SequenceMatcher(None, candidate_word, foil_word).ratio() >= 0.65
    )
