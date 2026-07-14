import re
from dataclasses import replace

from app.strategies.base import ConceptEdit

CONCEPT_CLASSES = (
    "relationship",
    "emotional_cause",
    "emotional_intensity",
    "urgency",
    "time",
    "place",
    "emotional_cue",
    "perspective",
)

_CONCEPT_ALIASES = {
    "relationship_type": "relationship",
    "social_relationship": "relationship",
    "cause": "emotional_cause",
    "emotion_cause": "emotional_cause",
    "emotional_trigger": "emotional_cause",
    "emotion_intensity": "emotional_intensity",
    "intensity": "emotional_intensity",
    "urgency_level": "urgency",
    "timing": "time",
    "temporal_context": "time",
    "location": "place",
    "setting": "place",
    "emotion_cue": "emotional_cue",
    "emotional_signal": "emotional_cue",
    "cue": "emotional_cue",
    "perspective_taking": "perspective",
    "point_of_view": "perspective",
    "perspective_or_knowledge": "perspective",
    "knowledge": "perspective",
}


def normalise_concept_class(value: str) -> str | None:
    key = re.sub(r"_+", "_", re.sub(r"[\s-]+", "_", value.strip().casefold()))
    canonical = _CONCEPT_ALIASES.get(key, key)
    return canonical if canonical in CONCEPT_CLASSES else None


def apply_concept_edit(
    scenario: str,
    edit: ConceptEdit,
) -> tuple[str, ConceptEdit] | None:
    """Apply one unambiguous span replacement and preserve original-text offsets."""

    exact_matches = list(re.finditer(re.escape(edit.original_span), scenario))
    if exact_matches:
        matches = exact_matches
    else:
        matches = list(
            re.finditer(
                re.escape(edit.original_span),
                scenario,
                flags=re.IGNORECASE,
            )
        )

    if len(matches) != 1:
        return None

    match = matches[0]
    actual_original = match.group(0)
    replacement_span = edit.replacement_span.strip()
    if not replacement_span or _normalise_text(actual_original) == _normalise_text(
        replacement_span
    ):
        return None

    modified = f"{scenario[: match.start()]}{replacement_span}{scenario[match.end() :]}"
    resolved_edit = replace(
        edit,
        original_span=actual_original,
        replacement_span=replacement_span,
    )
    return modified, resolved_edit


def describe_concept_edit(edit: ConceptEdit) -> str:
    return (
        f"{edit.concept_class}: '{edit.original_span}' -> "
        f"'{edit.replacement_span}'"
    )


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
