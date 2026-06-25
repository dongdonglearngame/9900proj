from time import perf_counter

from app.core.config import get_settings
from app.harness.logprobs import option_logprobs_to_probs
from app.harness.target_predict import PredictionResult
from app.schemas.common import ordered_choice_letters


class MockLLMClient:
    def predict(self, scenario: str, choices: dict[str, str], model: str) -> PredictionResult:
        started = perf_counter()
        lower = scenario.lower()
        ordered_letters = ordered_choice_letters(choices)
        answer = (
            "C"
            if ("early evening" in lower or "afternoon" in lower) and "C" in choices
            else "A"
            if "A" in choices
            else ordered_letters[0]
        )
        option_logprobs = _mock_option_logprobs(ordered_letters, answer)
        return PredictionResult(
            status="ok",
            answer=answer,
            answer_text=choices.get(answer),
            model=model,
            prompt_template_version=get_settings().target_prompt_version,
            cache_hit=False,
            raw_response=answer,
            option_logprobs=option_logprobs,
            option_probs=option_logprobs_to_probs(option_logprobs),
            top_logprobs_raw=[],
            runtime_seconds=round(perf_counter() - started, 4),
        )


def _mock_option_logprobs(ordered_letters: list[str], answer: str) -> dict[str, float | None]:
    scores = {letter: round(-3.6 - index * 0.35, 2) for index, letter in enumerate(ordered_letters)}
    scores[answer] = -0.35 if answer == "C" else -0.12

    if answer == "C" and "A" in scores:
        scores["A"] = -2.90
    if answer != "C" and "C" in scores:
        scores["C"] = -2.05
    if "B" in scores and answer != "B":
        scores["B"] = -3.40
    if "D" in scores and answer != "D":
        scores["D"] = None

    return scores
