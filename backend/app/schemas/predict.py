from pydantic import field_validator

from app.schemas.common import (
    APIModel,
    ChoiceLetter,
    ChoiceMap,
    OptionScoreMap,
    validate_choice_map,
)


class PredictRequest(APIModel):
    question_id: str | None = None
    scenario: str
    choices: ChoiceMap
    model: str

    @field_validator("choices")
    @classmethod
    def validate_choices(cls, choices: ChoiceMap) -> ChoiceMap:
        return validate_choice_map(choices)


class PredictionResponse(APIModel):
    status: str
    answer: ChoiceLetter | None
    answer_text: str | None
    model: str
    prompt_template_version: str
    cache_hit: bool
    raw_response: str
    option_logprobs: OptionScoreMap
    option_probs: OptionScoreMap
    runtime_seconds: float
