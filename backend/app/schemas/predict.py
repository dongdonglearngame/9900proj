from app.schemas.common import APIModel, ChoiceLetter, ChoiceMap, OptionScoreMap


class PredictRequest(APIModel):
    question_id: str | None = None
    scenario: str
    choices: ChoiceMap
    model: str


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
