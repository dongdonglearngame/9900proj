from dataclasses import dataclass, replace

from app.schemas.common import ChoiceLetter, OptionScoreMap


@dataclass(frozen=True)
class PredictionResult:
    status: str
    answer: ChoiceLetter | None
    answer_text: str | None
    model: str
    prompt_template_version: str
    cache_hit: bool
    raw_response: str
    option_logprobs: OptionScoreMap
    option_probs: OptionScoreMap
    top_logprobs_raw: list[dict]
    runtime_seconds: float

    def with_cache_hit(self) -> "PredictionResult":
        return replace(self, cache_hit=True)
