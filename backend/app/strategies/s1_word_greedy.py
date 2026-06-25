import re
from collections.abc import Iterable

from app.strategies.base import (
    AttemptRecord,
    CounterfactualResult,
    CounterfactualStrategy,
    TargetModel,
)

WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

DEMO_SEED_REPLACEMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("middle of the night", ("early evening", "afternoon")),
    ("late at night", ("early evening", "afternoon")),
)

TIME_PHRASE_REPLACEMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("after midnight", ("early evening", "afternoon")),
    ("at midnight", ("early evening", "afternoon")),
    ("overnight", ("during the afternoon", "early evening")),
    ("early morning", ("afternoon", "early evening")),
    ("late evening", ("afternoon", "early evening")),
    ("this morning", ("this evening", "this afternoon")),
    ("tonight", ("this afternoon", "this morning")),
    ("tomorrow", ("today",)),
    ("yesterday", ("today",)),
    ("after work", ("before work",)),
    ("before work", ("after work",)),
)

MODIFIER_WEAKENING: dict[str, tuple[str, ...]] = {
    "absolutely": ("somewhat",),
    "always": ("often",),
    "completely": ("partly",),
    "deeply": ("somewhat",),
    "desperately": ("somewhat",),
    "extremely": ("very", "somewhat"),
    "immediately": ("soon",),
    "never": ("rarely",),
    "really": ("somewhat",),
    "severely": ("moderately",),
    "totally": ("partly",),
    "very": ("somewhat", "slightly"),
}

EMOTION_INTENSITY_REPLACEMENTS: dict[str, tuple[str, ...]] = {
    "afraid": ("concerned",),
    "angry": ("annoyed", "upset"),
    "anxious": ("concerned",),
    "ashamed": ("embarrassed",),
    "crushed": ("sad",),
    "devastated": ("sad", "upset"),
    "enraged": ("angry", "upset"),
    "furious": ("angry", "upset"),
    "heartbroken": ("sad",),
    "horrified": ("worried",),
    "lonely": ("alone", "calm"),
    "miserable": ("sad",),
    "panicked": ("worried", "concerned"),
    "terrified": ("worried", "concerned"),
    "thrilled": ("pleased",),
    "upset": ("concerned",),
}

LOCAL_LEXICAL_SWAPS: dict[str, tuple[str, ...]] = {
    "alone": ("supported", "with others"),
    "avoid": ("approach",),
    "blame": ("support",),
    "close": ("distant",),
    "delay": ("respond",),
    "distant": ("close",),
    "ignore": ("answer", "acknowledge"),
    "ignored": ("answered", "acknowledged"),
    "leave": ("stay",),
    "public": ("private",),
    "reject": ("accept",),
    "rude": ("polite",),
    "safe": ("unsafe",),
    "unsafe": ("safe",),
    "urgent": ("not urgent",),
}

CONTROLLED_INSERTIONS: tuple[str, ...] = (
    "It is early evening.",
    "The situation is not urgent.",
    "The person is physically safe.",
)

STOPWORDS = {
    "a",
    "about",
    "after",
    "all",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "but",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "hers",
    "him",
    "his",
    "i",
    "in",
    "is",
    "it",
    "its",
    "my",
    "of",
    "on",
    "or",
    "our",
    "she",
    "that",
    "the",
    "their",
    "them",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "with",
    "you",
    "your",
}


class S1WordGreedyStrategy(CounterfactualStrategy):
    """S1 word-level greedy baseline.

    The first generator preserves the seeded demo edits. The remaining generators
    form the systematic baseline used for broader comparison: time substitutions,
    emotion/modifier weakening, local lexical swaps, small controlled insertions,
    and content-word deletion.
    """

    id = "s1_word_greedy"
    name = "S1 Word-level Greedy"

    def generate(
        self,
        scenario: str,
        choices: dict[str, str],
        model: TargetModel,
        foil: str,
        budget: int,
    ) -> CounterfactualResult:
        attempts: list[AttemptRecord] = []
        budget = max(budget, 0)

        for modified_scenario, description in self._generate_candidates(scenario):
            if len(attempts) >= budget:
                break

            prediction = model.target_predict(modified_scenario, choices)
            success = prediction.answer == foil
            attempts.append(
                AttemptRecord(
                    modified_scenario=modified_scenario,
                    prediction=prediction,
                    success=success,
                    edit_description=description,
                )
            )

            if success:
                return CounterfactualResult(
                    status="success",
                    original_scenario=scenario,
                    modified_scenario=modified_scenario,
                    new_answer=prediction.answer,
                    foil=foil,
                    strategy_id=self.id,
                    attempts=attempts,
                    message=None,
                )

        return CounterfactualResult(
            status="not_found",
            original_scenario=scenario,
            modified_scenario=None,
            new_answer=None,
            foil=foil,
            strategy_id=self.id,
            attempts=attempts,
            message="no S1 candidate flipped the factual scenario within budget",
        )

    def _generate_candidates(self, scenario: str) -> Iterable[tuple[str, str]]:
        seen: set[str] = set()
        generators = (
            _seed_demo_candidates,
            _time_phrase_candidates,
            _modifier_weakening_candidates,
            _emotion_intensity_candidates,
            _local_lexical_swap_candidates,
            _controlled_insertion_candidates,
            _content_word_deletion_candidates,
        )

        for generator in generators:
            for candidate, description in generator(scenario):
                normalised = _normalise_spaces(candidate)
                if normalised == scenario or normalised in seen:
                    continue
                seen.add(normalised)
                yield normalised, description


def _seed_demo_candidates(scenario: str) -> Iterable[tuple[str, str]]:
    yield from _literal_replacement_candidates(
        scenario,
        DEMO_SEED_REPLACEMENTS,
        description_prefix="seed replacement",
    )


def _time_phrase_candidates(scenario: str) -> Iterable[tuple[str, str]]:
    yield from _literal_replacement_candidates(
        scenario,
        TIME_PHRASE_REPLACEMENTS,
        description_prefix="time phrase substitution",
    )


def _modifier_weakening_candidates(scenario: str) -> Iterable[tuple[str, str]]:
    yield from _word_replacement_candidates(
        scenario,
        MODIFIER_WEAKENING,
        description_prefix="modifier weakening",
    )


def _emotion_intensity_candidates(scenario: str) -> Iterable[tuple[str, str]]:
    yield from _word_replacement_candidates(
        scenario,
        EMOTION_INTENSITY_REPLACEMENTS,
        description_prefix="emotion intensity substitution",
    )


def _local_lexical_swap_candidates(scenario: str) -> Iterable[tuple[str, str]]:
    yield from _word_replacement_candidates(
        scenario,
        LOCAL_LEXICAL_SWAPS,
        description_prefix="local lexical swap",
    )


def _controlled_insertion_candidates(scenario: str) -> Iterable[tuple[str, str]]:
    stripped = scenario.strip()
    if not stripped:
        return

    for insertion in CONTROLLED_INSERTIONS:
        candidate = f"{stripped} {insertion}"
        yield candidate, f"insert '{insertion}'"


def _content_word_deletion_candidates(scenario: str) -> Iterable[tuple[str, str]]:
    for match in WORD_RE.finditer(scenario):
        word = match.group(0)
        lower = word.lower()
        if lower in STOPWORDS or len(lower) <= 2:
            continue

        candidate = _replace_span(scenario, match.start(), match.end(), "")
        if len(candidate.split()) < 3:
            continue
        yield candidate, f"delete content word '{word}'"


def _literal_replacement_candidates(
    scenario: str,
    replacements: tuple[tuple[str, tuple[str, ...]], ...],
    *,
    description_prefix: str,
) -> Iterable[tuple[str, str]]:
    lower = scenario.lower()

    for source, options in replacements:
        start = 0
        while True:
            index = lower.find(source, start)
            if index == -1:
                break

            original_span = scenario[index : index + len(source)]
            for replacement in options:
                candidate = _replace_span(
                    scenario,
                    index,
                    index + len(source),
                    _match_initial_case(original_span, replacement),
                )
                yield (
                    candidate,
                    f"{description_prefix}: replace '{original_span}' with '{replacement}'",
                )

            start = index + len(source)


def _word_replacement_candidates(
    scenario: str,
    replacements: dict[str, tuple[str, ...]],
    *,
    description_prefix: str,
) -> Iterable[tuple[str, str]]:
    for match in WORD_RE.finditer(scenario):
        original_word = match.group(0)
        options = replacements.get(original_word.lower())
        if not options:
            continue

        for replacement in options:
            candidate = _replace_span(
                scenario,
                match.start(),
                match.end(),
                _match_initial_case(original_word, replacement),
            )
            yield (
                candidate,
                f"{description_prefix}: replace '{original_word}' with '{replacement}'",
            )


def _replace_span(scenario: str, start: int, end: int, replacement: str) -> str:
    prefix = scenario[:start]
    suffix = scenario[end:]
    if replacement:
        return f"{prefix}{replacement}{suffix}"

    prefix = prefix.rstrip()
    suffix = suffix.lstrip()
    if not prefix:
        return suffix
    if not suffix:
        return prefix
    if suffix[:1] in {".", ",", ";", ":", "?", "!"}:
        return f"{prefix}{suffix}"
    return f"{prefix} {suffix}"


def _normalise_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _match_initial_case(original: str, replacement: str) -> str:
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement
