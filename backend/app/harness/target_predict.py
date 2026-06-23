from dataclasses import dataclass, replace
from typing import Literal

ChoiceLetter = Literal["A", "B", "C", "D"]


@dataclass(frozen=True)
class PredictionResult:
    status: str
    answer: ChoiceLetter | None
    answer_text: str | None
    model: str
    prompt_template_version: str
    cache_hit: bool
    raw_response: str
    option_logprobs: dict[ChoiceLetter, float | None]
    option_probs: dict[ChoiceLetter, float | None]
    top_logprobs_raw: list[dict]
    runtime_seconds: float

    def with_cache_hit(self) -> "PredictionResult":
        return replace(self, cache_hit=True)
