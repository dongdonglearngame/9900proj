import json


def build_concept_proposer_messages(
    scenario: str,
    choices: dict[str, str],
    foil: str,
    original_answer: str,
    count: int,
    allowed_concepts: tuple[str, ...],
    avoid: list[str] | None = None,
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
                "answer text. Prefer distinct concept classes. Return JSON only: "
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
