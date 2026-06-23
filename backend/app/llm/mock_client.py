from time import perf_counter

from app.core.config import get_settings
from app.harness.target_predict import PredictionResult


class MockLLMClient:
    def predict(self, scenario: str, choices: dict[str, str], model: str) -> PredictionResult:
        started = perf_counter()
        lower = scenario.lower()
        answer = "C" if "early evening" in lower or "afternoon" in lower else "A"
        return PredictionResult(
            status="ok",
            answer=answer,
            answer_text=choices.get(answer),
            model=model,
            prompt_template_version=get_settings().target_prompt_version,
            cache_hit=False,
            raw_response=answer,
            option_logprobs={
                "A": -2.90 if answer == "C" else -0.12,
                "B": -3.40,
                "C": -0.35 if answer == "C" else -2.05,
                "D": None,
            },
            option_probs={
                "A": 0.055 if answer == "C" else 0.886,
                "B": 0.033,
                "C": 0.705 if answer == "C" else 0.129,
                "D": None,
            },
            top_logprobs_raw=[],
            runtime_seconds=round(perf_counter() - started, 4),
        )
