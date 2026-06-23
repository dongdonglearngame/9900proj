from app.schemas.common import APIModel, ChoiceLetter, ChoiceMap


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


class ScenariosResponse(APIModel):
    items: list[ScenarioItem]
    total: int
