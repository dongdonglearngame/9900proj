import json
from typing import Literal

S2PromptVariant = Literal[
    "v5_baseline",
    "zero_shot",
    "one_shot",
    "few_shot",
    "span_grounded",
]

S2_DEFAULT_PROMPT_VARIANT: S2PromptVariant = "v5_baseline"
S2_PROMPT_VERSIONS: dict[S2PromptVariant, str] = {
    "v5_baseline": "s2-proposer-v5-coherence-checklist",
    "zero_shot": "s2-proposer-v6-zero-shot",
    "one_shot": "s2-proposer-v6-one-shot-curated",
    "few_shot": "s2-proposer-v6-1-three-shot-curated",
    "span_grounded": "s2-proposer-v7-span-grounded-spike",
}
# Backwards-compatible alias for callers that only need the production default.
S2_PROPOSER_PROMPT_VERSION = S2_PROMPT_VERSIONS[S2_DEFAULT_PROMPT_VARIANT]
S2_PREFERRED_MAX_CHANGED_WORDS = 3
S2_MAX_CHANGED_WORDS = 6
S2_FALLBACK_MAX_CHANGED_WORDS = 6
S4_INFILL_PROMPT_VERSION = "s4-infill-v1"

_CURATED_POSITIVE_EXAMPLES = (
    (
        "original='Leah submitted the form, but the committee rejected it after "
        "review.' good_rewrite='Leah submitted the form, but the committee approved "
        "it after review.' This changes one outcome word inside the existing sentence."
    ),
    (
        "original='Noah asked his teammate for help, but she ignored his request.' "
        "good_rewrite='Noah asked his teammate for help, but she answered his "
        "request.' This changes one observable behaviour without stating an emotion."
    ),
    (
        'original="Tariq\'s neighbour refused to return the borrowed keys." '
        'good_rewrite="Tariq\'s neighbour agreed to return the borrowed keys." This '
        "changes one relationship behaviour and preserves the actor and event."
    ),
)

_V5_BASELINE_EXAMPLES = (
    "Quality example: original='Maya submitted her proposal, but her manager rejected "
    "it without explanation.' good_rewrite='Maya submitted her proposal, and her "
    "manager approved it without hesitation.' This changes three words inside the "
    "existing sentence and keeps the story grammatical. Bad example: 'Maya submitted "
    "her proposal, but her manager rejected it without explanation. Everything was "
    "suddenly fine.' This appends an unsupported generic sentence instead of editing "
    "the event. Use the examples only as quality guidance; never copy them. Another "
    "bad example: original='Omar won the race. He raised the trophy.' rewrite='Omar "
    "reached the final. He raised the trophy.' The unchanged trophy sentence relies "
    "on the removed win. A bad focal-person example is original='Kai lost the match.' "
    "rewrite='The crowd cheered loudly.' The rewrite drops Kai's outcome and substitutes "
    "a bystander reaction."
)

_SPAN_GROUNDED_EXAMPLES = (
    "Use these synthetic span examples only as structural guidance: "
    "original='Leah submitted the form, but the committee rejected it after review.' "
    "edit={\"original_span\":\"rejected\",\"replacement_span\":\"approved\","
    "\"change_type\":\"outcome\"}; "
    "original='Noah asked his teammate for help, but she ignored his request.' "
    "edit={\"original_span\":\"ignored\",\"replacement_span\":\"answered\","
    "\"change_type\":\"behaviour\"}; "
    "original=\"Tariq's neighbour refused to return the borrowed keys.\" "
    "edit={\"original_span\":\"refused\",\"replacement_span\":\"agreed\","
    "\"change_type\":\"relationship\"}. Never copy the example wording."
)


def s2_prompt_version(variant: S2PromptVariant) -> str:
    return S2_PROMPT_VERSIONS[variant]


def build_proposer_messages(
    scenario: str,
    choices: dict[str, str],
    foil: str,
    original_answer: str,
    count: int,
    avoid: list[str] | None = None,
    preferred_max_changed_words: int = S2_PREFERRED_MAX_CHANGED_WORDS,
    max_changed_words: int = S2_MAX_CHANGED_WORDS,
    variant: S2PromptVariant = S2_DEFAULT_PROMPT_VARIANT,
) -> list[dict[str, str]]:
    payload = {
        "scenario": scenario,
        "choices": choices,
        "original_answer": original_answer,
        "foil": foil,
        "count": count,
        "avoid": avoid or [],
        "constraints": {
            "modify_exactly_one_existing_sentence": True,
            "allow_new_sentences": False,
            "preferred_max_changed_words": preferred_max_changed_words,
            "hard_max_changed_words": max_changed_words,
        },
    }
    if variant == "span_grounded":
        payload["constraints"]["output_mode"] = "exact_span_replacement"
    examples = _examples_for_variant(variant)
    output_contract = _output_contract(variant)
    system_content = (
        "You propose minimal counterfactual rewrites for emotion-reasoning "
        "multiple-choice scenarios. You may see the target foil, but the frozen "
        "target model will not. Change an underlying event, outcome, relationship, "
        "or observable behaviour rather than directly naming or paraphrasing the "
        "target emotion or answer. Modify exactly one existing sentence and do not "
        "append, prepend, split, or merge sentences. Prefer changing no more than "
        f"{preferred_max_changed_words} words and never change more than "
        f"{max_changed_words} words. Preserve the surrounding facts, actors, tense, "
        "grammar, and narrative coherence. Rewrite only the scenario, keep it fluent "
        "and realistic, do not mention option letters, and do not copy or "
        "morphologically derive any option answer text in the scenario. "
        "Do not add a sentence or clause whose purpose is to state how a person "
        "feels; express the change through an observable event, outcome, relationship, "
        "or behaviour. Do not propose an edit that makes unchanged sentences "
        "contradict the modified fact. Keep the changed sentence about the same focal "
        "person or event and preserve at least one meaningful content word from that "
        "sentence. Never replace a focal person's outcome with a reaction by the "
        "crowd or another bystander. Before returning each rewrite, silently check "
        "every unchanged sentence for references to a fact the rewrite removed. "
        f"{examples}"
        "Return exactly the requested number of distinct rewrites and use a different "
        "change mechanism where possible. Treat avoid entries as prior failures and "
        "do not repeat them. "
        f"{output_contract}"
    )
    return [
        {
            "role": "system",
            "content": system_content,
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        },
    ]


def _examples_for_variant(variant: S2PromptVariant) -> str:
    if variant == "v5_baseline":
        return f"{_V5_BASELINE_EXAMPLES} "
    if variant == "zero_shot":
        return ""
    if variant == "span_grounded":
        return f"{_SPAN_GROUNDED_EXAMPLES} "
    example_count = 1 if variant == "one_shot" else len(_CURATED_POSITIVE_EXAMPLES)
    examples = " ".join(_CURATED_POSITIVE_EXAMPLES[:example_count])
    return (
        "Use these synthetic quality examples only as structural guidance and never "
        f"copy their wording: {examples} "
    )


def _output_contract(variant: S2PromptVariant) -> str:
    if variant == "span_grounded":
        return (
            "Return JSON only. Do not return a rewritten scenario. For each candidate, "
            "copy one exact, contiguous, uniquely occurring original_span from the "
            "scenario and provide a non-empty replacement_span of no more than 3 words. "
            "The application will perform the replacement deterministically: "
            '{"rewrites":[{"original_span":"...","replacement_span":"...",'
            '"change_type":"event|outcome|relationship|behaviour",'
            '"rationale":"..."}]}.'
        )
    return (
        "Return JSON only; modified_scenario is required and changed_span, "
        "change_type, and rationale are optional: "
        '{"rewrites":[{"modified_scenario":"...","changed_span":"...",'
        '"change_type":"event|outcome|relationship|behaviour",'
        '"rationale":"..."}]}.'
    )


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
