from app.schemas.common import ChoiceMap, ordered_choice_letters


def build_target_system_prompt(choices: ChoiceMap) -> str:
    letters = ordered_choice_letters(choices)
    joined_letters = (
        letters[0]
        if len(letters) == 1
        else " or ".join(letters)
        if len(letters) == 2
        else f"{', '.join(letters[:-1])}, or {letters[-1]}"
    )
    return (
        "You answer multiple-choice emotional reasoning questions. "
        f"Return only one letter {joined_letters}. Do not explain."
    )


def build_target_user_prompt(scenario: str, choices: ChoiceMap) -> str:
    choice_lines = [f"{letter}. {choices[letter]}" for letter in ordered_choice_letters(choices)]
    return "\n".join(
        [
            "Scenario",
            scenario,
            "",
            "Choices",
            *choice_lines,
            "",
            "Answer with exactly one letter.",
            "Answer",
        ]
    )


def build_target_messages(scenario: str, choices: ChoiceMap) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": build_target_system_prompt(choices)},
        {"role": "user", "content": build_target_user_prompt(scenario, choices)},
    ]
