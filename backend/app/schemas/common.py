import string

from pydantic import BaseModel, ConfigDict

ChoiceLetter = str
ChoiceMap = dict[str, str]
OptionScoreMap = dict[str, float | None]


def letters_for(count: int) -> list[str]:
    if count < 1 or count > len(string.ascii_uppercase):
        raise ValueError("choices must contain between 1 and 26 options")
    return list(string.ascii_uppercase[:count])


def ordered_choice_letters(choices: ChoiceMap) -> list[str]:
    return sorted(choices)


def validate_choice_map(choices: ChoiceMap) -> ChoiceMap:
    if len(choices) < 2:
        raise ValueError("choices must contain at least two options")

    expected = letters_for(len(choices))
    actual = ordered_choice_letters(choices)
    if actual != expected:
        raise ValueError(
            "choices keys must be contiguous uppercase letters starting at A "
            f"(expected {expected}, got {actual})"
        )

    for letter, text in choices.items():
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"choice {letter} must be a non-empty string")

    return choices


def validate_choice_letter(
    letter: ChoiceLetter,
    choices: ChoiceMap,
    field_name: str,
) -> ChoiceLetter:
    if letter not in choices:
        allowed = ", ".join(ordered_choice_letters(choices))
        raise ValueError(f"{field_name} must be one of: {allowed}")
    return letter


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ModelInfo(APIModel):
    id: str
    name: str
    available: bool


class ModelsResponse(APIModel):
    models: list[ModelInfo]
