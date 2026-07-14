import json

S2_PROPOSER_PROMPT_VERSION = "s2-proposer-v2-event-grounded"
S4_INFILL_PROMPT_VERSION = "s4-infill-v1"


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
                "target model will not. Change an underlying event, outcome, relationship, "
                "or observable behaviour rather than directly naming or paraphrasing the "
                "target emotion or answer. Rewrite only the scenario, keep it fluent and "
                "realistic, do not mention option letters, and do not copy or morphologically "
                "derive any option answer text in the scenario. Return exactly the requested "
                "number of distinct rewrites and use a different change mechanism where "
                "possible. Treat avoid entries as prior failures and do not repeat them. "
                "Return JSON only; modified_scenario is required and changed_span, "
                "change_type, and rationale are optional: "
                '{"rewrites":[{"modified_scenario":"...","changed_span":"...",'
                '"change_type":"event|outcome|relationship|behaviour",'
                '"rationale":"..."}]}.'
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        },
    ]


def build_infill_messages(
    original_scenario: str,
    masked_scenario: str,
    choices: dict[str, str],
    foil: str,
    original_answer: str,
    count: int,
    avoid: list[str] | None = None,
) -> list[dict[str, str]]:
    payload = {
        "original_scenario": original_scenario,
        "masked_scenario": masked_scenario,
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
                "You fill masked spans in emotion-reasoning multiple-choice scenarios. "
                "You may see the target foil, but the frozen target model will not. "
                "Only replace each [MASK] span. Preserve every unmasked character exactly, "
                "keep the final scenario fluent and realistic, do not mention option "
                "letters, and do not copy any option answer text into the scenario. "
                "Return JSON only: "
                '{"rewrites":[{"modified_scenario":"...","rationale":"..."}]}.'
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        },
    ]
