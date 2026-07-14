import logging
import re
from dataclasses import dataclass
from typing import Any

from app.proposer.clients import ProposerCompletion
from app.proposer.concepts import normalise_concept_class
from app.proposer.json_utils import load_json_payload
from app.strategies.base import ConceptEdit

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConceptEditParseResult:
    edits: list[ConceptEdit]
    raw_candidates: int
    parsed_candidates: int


def parse_concept_edits(
    raw: str | ProposerCompletion,
    *,
    limit: int,
    allowed_concepts: tuple[str, ...],
) -> list[ConceptEdit]:
    return parse_concept_edits_with_diagnostics(
        raw,
        limit=limit,
        allowed_concepts=allowed_concepts,
    ).edits


def parse_concept_edits_with_diagnostics(
    raw: str | ProposerCompletion,
    *,
    limit: int,
    allowed_concepts: tuple[str, ...],
) -> ConceptEditParseResult:
    if limit <= 0:
        return ConceptEditParseResult([], 0, 0)
    raw_text = raw.content if isinstance(raw, ProposerCompletion) else raw
    payload = load_json_payload(raw_text)
    if payload is None:
        return ConceptEditParseResult([], 0, 0)

    items = payload.get("edits") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return ConceptEditParseResult([], 0, 0)

    allowed = set(allowed_concepts)
    edits: list[ConceptEdit] = []
    for item in items:
        edit = _coerce_concept_edit(item, allowed)
        if edit is None:
            continue
        edits.append(edit)
    return ConceptEditParseResult(
        edits=edits[:limit],
        raw_candidates=len(items),
        parsed_candidates=len(edits),
    )


def _coerce_concept_edit(item: Any, allowed: set[str]) -> ConceptEdit | None:
    if not isinstance(item, dict):
        return None

    raw_concept = item.get("concept_class")
    if not isinstance(raw_concept, str):
        return None
    concept_class = normalise_concept_class(raw_concept)
    if concept_class is None or concept_class not in allowed:
        logger.warning("Rejected unknown concept class %r", raw_concept)
        return None

    original_span = _required_string(item.get("original_span"))
    replacement_span = _required_string(item.get("replacement_span"))
    if original_span is None or replacement_span is None:
        return None
    if _normalise_text(original_span) == _normalise_text(replacement_span):
        return None

    return ConceptEdit(
        concept_class=concept_class,
        original_span=original_span,
        replacement_span=replacement_span,
        source_value=_optional_string(item.get("source_value")),
        target_value=_optional_string(item.get("target_value")),
        rationale=_optional_string(item.get("rationale")),
    )


def _required_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _optional_string(value: Any) -> str | None:
    return _required_string(value)


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
