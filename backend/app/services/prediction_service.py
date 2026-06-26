from functools import lru_cache

from app.core.config import get_settings
from app.db.hashing import prediction_cache_key
from app.harness.target_predict import PredictionResult
from app.llm.mock_client import MockLLMClient
from app.llm.ollama_client import OllamaClient
from app.repositories.prediction_repo import PredictionRepository
from app.schemas.predict import PredictionResponse, PredictRequest


class PredictionService:
    """Wraps the frozen target harness and caches predictions.

    The frozen invariants live in the client + harness (stateless, temperature 0, foil
    never in the prompt, argmax flip). In mock mode this uses MockLLMClient; with
    USE_MOCK_LLM=false it uses OllamaClient.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = MockLLMClient() if settings.use_mock_llm else OllamaClient()
        self._repo = PredictionRepository()

    def predict(self, request: PredictRequest) -> PredictionResponse:
        result = self.target_predict(
            scenario=request.scenario,
            choices=request.choices,
            model=request.model,
        )
        return self._to_response(result)

    def target_predict(
        self,
        scenario: str,
        choices: dict[str, str],
        model: str,
    ) -> PredictionResult:
        cache_key = prediction_cache_key(
            model=model,
            prompt_template_version=get_settings().target_prompt_version,
            scenario=scenario,
            choices=choices,
        )
        cached = self._repo.get(cache_key)
        if cached:
            return cached.with_cache_hit()

        result = self._client.predict(scenario=scenario, choices=choices, model=model)
        self._repo.set(cache_key, result)
        return result

    def _to_response(self, result: PredictionResult) -> PredictionResponse:
        return PredictionResponse(
            status=result.status,
            answer=result.answer,
            answer_text=result.answer_text,
            model=result.model,
            prompt_template_version=result.prompt_template_version,
            cache_hit=result.cache_hit,
            raw_response=result.raw_response,
            option_logprobs=result.option_logprobs,
            option_probs=result.option_probs,
            runtime_seconds=result.runtime_seconds,
        )


@lru_cache
def get_prediction_service() -> PredictionService:
    """Single shared instance so /predict and the counterfactual search share one
    client and one cache."""
    return PredictionService()
