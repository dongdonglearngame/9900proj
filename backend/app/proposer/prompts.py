import json


def build_proposer_messages(
    scenario: str,
    choices: dict[str, str],
    foil: str,
    original_answer: str,
    count: int,
    avoid: list[str] | None = None,
) -> list[dict[str, str]]:
    payload = {
        "scenario": scenario,
        "choices": choices,
        "original_answer": original_answer,
        "foil": foil,
        "count": count,
        "avoid": avoid or [],
    }
    return [
        {
            "role": "system",
            "content": (
                "You propose minimal counterfactual rewrites for emotion-reasoning "
                "multiple-choice scenarios. You may see the target foil, but the frozen "
                "target model will not. Rewrite only the scenario, keep it fluent and "
                "realistic, do not mention option letters, and do not copy any option "
                "answer text into the scenario. Return JSON only: "
                '{"rewrites":[{"modified_scenario":"...","rationale":"..."}]}.'
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        },
    ]
