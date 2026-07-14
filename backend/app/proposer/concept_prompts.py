import json

from app.strategies.base import ConceptEdit, ConceptEditKey

S6_CONCEPT_PROMPT_VERSION = "s6-concept-v2-grounded-diverse"
S6_CONCEPT_REPAIR_PROMPT_VERSION = "s6-concept-repair-v1"


def build_concept_proposer_messages(
    scenario: str,
    choices: dict[str, str],
    foil: str,
    original_answer: str,
    count: int,
    allowed_concepts: tuple[str, ...],
    avoid: list[str] | None = None,
    used_edits: list[ConceptEditKey] | None = None,
) -> list[dict[str, str]]:
    payload = {
        "mode": "concept_edit",
        "scenario": scenario,
        "choices": choices,
        "original_answer": original_answer,
        "foil": foil,
        "count": count,
        "allowed_concepts": list(allowed_concepts),
        "avoid": avoid or [],
        "used_edits": _used_edit_payloads(used_edits or []),
    }
    return [
        {
            "role": "system",
            "content": (
                "You propose causal-inspired concept interventions for emotion-reasoning "
                "scenarios. Each edit must change exactly one allowed concept through one "
                "contiguous span replacement while keeping every other fact and concept fixed. "
                "Copy original_span exactly from the scenario. Return only the replacement, not "
                "a rewritten full scenario. Do not mention option letters or copy any option "
                "answer text. Return exactly the requested number of edits. Within this response, "
                "use different concept classes and original spans where possible. Do not repeat "
                "any concept/span/target tuple in used_edits or avoid. Return JSON only: "
                '{"edits":[{"concept_class":"time","original_span":"...",'
                '"replacement_span":"...","source_value":"...",'
                '"target_value":"...","rationale":"..."}]}.'
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        },
    ]


def build_concept_repair_messages(
    scenario: str,
    choices: dict[str, str],
    foil: str,
    original_answer: str,
    edit: ConceptEdit,
    allowed_concepts: tuple[str, ...],
    used_edits: list[ConceptEditKey] | None = None,
) -> list[dict[str, str]]:
    payload = {
        "mode": "concept_edit_repair",
        "scenario": scenario,
        "choices": choices,
        "original_answer": original_answer,
        "foil": foil,
        "count": 1,
        "allowed_concepts": list(allowed_concepts),
        "invalid_edit": _concept_edit_payload(edit),
        "used_edits": _used_edit_payloads(used_edits or []),
    }
    return [
        {
            "role": "system",
            "content": (
                "Repair only the grounding of one causal-inspired concept edit. Return exactly "
                "one edit with an original_span copied verbatim from the scenario that occurs "
                "exactly once. Preserve the supplied concept_class, replacement_span, "
                "source_value, and target_value; do not invent a different intervention or "
                "rewrite the full scenario. Do not mention option letters or copy answer text. "
                "Return JSON only in the same edits schema."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        },
    ]


def _concept_edit_payload(edit: ConceptEdit) -> dict[str, str | None]:
    return {
        "concept_class": edit.concept_class,
        "original_span": edit.original_span,
        "replacement_span": edit.replacement_span,
        "source_value": edit.source_value,
        "target_value": edit.target_value,
        "rationale": edit.rationale,
    }


def _used_edit_payloads(edits: list[ConceptEditKey]) -> list[dict[str, str]]:
    return [
        {
            "concept_class": concept_class,
            "original_span": original_span,
            "target_value": target_value,
        }
        for concept_class, original_span, target_value in edits
    ]
