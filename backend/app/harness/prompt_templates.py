TARGET_SYSTEM_PROMPT = (
    "You answer multiple-choice emotional reasoning questions. "
    "Return only one letter A, B, C, or D. Do not explain."
)


def build_target_user_prompt(scenario: str, choices: dict[str, str]) -> str:
    return "\n".join(
        [
            "Scenario",
            scenario,
            "",
            "Choices",
            f"A. {choices['A']}",
            f"B. {choices['B']}",
            f"C. {choices['C']}",
            f"D. {choices['D']}",
            "",
            "Answer with exactly one letter.",
            "Answer",
        ]
    )


def build_target_messages(scenario: str, choices: dict[str, str]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": TARGET_SYSTEM_PROMPT},
        {"role": "user", "content": build_target_user_prompt(scenario, choices)},
    ]
