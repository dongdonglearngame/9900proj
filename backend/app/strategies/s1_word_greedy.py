import re
from collections.abc import Iterable

from app.strategies.base import (
    AttemptRecord,
    CounterfactualResult,
    CounterfactualStrategy,
    TargetModel,
)

PHRASE_REPLACEMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("middle of the night", ("early evening", "afternoon")),
    ("late at night", ("early evening", "afternoon")),
    ("very late", ("earlier",)),
    ("urgent", ("not urgent",)),
    ("furious", ("upset",)),
    ("very angry", ("slightly upset",)),
    ("angry", ("upset",)),
    ("lonely", ("calm",)),
    ("devastated", ("sad",)),
    ("extremely upset", ("upset",)),
)

EMOTION_REPLACEMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("panicked", ("worried", "calm")),
    ("panic", ("worry",)),
    ("terrified", ("worried",)),
    ("anxious", ("concerned", "calm")),
    ("overwhelmed", ("concerned",)),
)

CONTENT_WORD_STOPWORDS = frozenset(
    {
        "about",
        "after",
        "again",
        "also",
        "before",
        "from",
        "into",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "this",
        "with",
        "would",
        "your",
    }
)

WORD_PATTERN = re.compile(r"\b[A-Za-z][A-Za-z'-]*\b")


class S1WordGreedyStrategy(CounterfactualStrategy):
    """S1 word-level greedy baseline.

    The strategy proposes deterministic, local phrase replacements, deduplicates
    candidates, and lets the shared target harness decide whether a flip happened.
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

        for candidate, description in _replacement_candidates(
            scenario,
            (*PHRASE_REPLACEMENTS, *EMOTION_REPLACEMENTS),
        ):
            if candidate in seen:
                continue
            seen.add(candidate)
            yield candidate, description

        for candidate, description in _content_word_deletion_candidates(scenario):
            if candidate in seen:
                continue
            seen.add(candidate)
            yield candidate, description


def _replacement_candidates(
    scenario: str,
    replacements_by_source: tuple[tuple[str, tuple[str, ...]], ...],
) -> Iterable[tuple[str, str]]:
    lower = scenario.lower()

    for source, replacements in replacements_by_source:
        start = 0
        while True:
            index = lower.find(source, start)
            if index == -1:
                break

            original_span = scenario[index : index + len(source)]
            for replacement in replacements:
                candidate = (
                    scenario[:index]
                    + _match_initial_case(original_span, replacement)
                    + scenario[index + len(source) :]
                )
                if candidate == scenario:
                    continue
                yield candidate, f"replace '{original_span}' with '{replacement}'"

            start = index + len(source)


def _content_word_deletion_candidates(scenario: str) -> Iterable[tuple[str, str]]:
    for match in WORD_PATTERN.finditer(scenario):
        word = match.group(0)
        normalized = word.lower().strip("'-")
        if len(normalized) < 4 or normalized in CONTENT_WORD_STOPWORDS:
            continue

        candidate = scenario[: match.start()] + scenario[match.end() :]
        candidate = _normalize_deleted_word_spacing(candidate)
        if candidate == scenario or not candidate:
            continue

        yield candidate, f"delete '{word}'"


def _normalize_deleted_word_spacing(candidate: str) -> str:
    candidate = re.sub(r"\s+([,.!?;:])", r"\1", candidate)
    candidate = re.sub(r"\s{2,}", " ", candidate)
    return candidate.strip()


def _match_initial_case(original: str, replacement: str) -> str:
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement
