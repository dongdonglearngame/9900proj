from pydantic import field_validator, model_validator

from app.schemas.common import (
    APIModel,
    ChoiceLetter,
    ChoiceMap,
    validate_choice_letter,
    validate_choice_map,
)


class ScenarioItem(APIModel):
    question_id: str
    scenario_item_id: str
    task_type: str
    dimension: str
    subject: str | None = None
    scenario: str
    question_text: str | None = None
    choices: ChoiceMap
    label: ChoiceLetter | None = None

    @field_validator("choices")
    @classmethod
    def validate_choices(cls, choices: ChoiceMap) -> ChoiceMap:
        return validate_choice_map(choices)

    @model_validator(mode="after")
    def validate_label(self) -> "ScenarioItem":
        if self.label is not None:
            validate_choice_letter(self.label, self.choices, "label")
        return self


class ScenariosResponse(APIModel):
    items: list[ScenarioItem]
    total: int
