import logging
from time import perf_counter
from typing import Any

import httpx

from app.core.config import get_settings
from app.harness.logprobs import extract_option_logprobs, option_logprobs_to_probs
from app.harness.parser import parse_answer_letter
from app.harness.prompt_templates import build_target_messages
from app.harness.target_predict import PredictionResult

logger = logging.getLogger(__name__)


class OllamaClient:
    """Frozen target-model client for deterministic Ollama chat inference."""

    def predict(self, scenario: str, choices: dict[str, str], model: str) -> PredictionResult:
        settings = get_settings()
        started = perf_counter()

        data = self._call(scenario, choices, model, settings)
        raw_response = self._content(data)
        answer = parse_answer_letter(raw_response, choices)

        if answer is None:
            logger.warning(
                "Ollama response could not be parsed as a valid choice letter; retrying once",
                extra={"model": model, "raw_response": raw_response},
            )
            data = self._call(scenario, choices, model, settings)
            raw_response = self._content(data)
            answer = parse_answer_letter(raw_response, choices)

        if answer is None:
            logger.warning(
                "Ollama response parse failed after retry",
                extra={"model": model, "raw_response": raw_response},
            )

        option_logprobs = extract_option_logprobs(data, choices)
        option_probs = option_logprobs_to_probs(option_logprobs)
        return PredictionResult(
            status="ok" if answer else "parse_failed",
            answer=answer,
            answer_text=choices.get(answer) if answer else None,
            model=model,
            prompt_template_version=settings.target_prompt_version,
            cache_hit=False,
            raw_response=raw_response,
            option_logprobs=option_logprobs,
            option_probs=option_probs,
            top_logprobs_raw=self._top_logprobs_raw(data),
            runtime_seconds=round(perf_counter() - started, 4),
        )

    def _call(
        self,
        scenario: str,
        choices: dict[str, str],
        model: str,
        settings: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": build_target_messages(scenario, choices),
            "stream": False,
            "keep_alive": "10m",
            "logprobs": True,
            "top_logprobs": settings.top_logprobs,
            "options": {
                "temperature": 0,
                "num_predict": settings.target_num_predict,
            },
        }
        response = httpx.post(
            f"{settings.ollama_base_url}/api/chat",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _content(data: dict[str, Any]) -> str:
        message = data.get("message")
        if not isinstance(message, dict):
            return ""
        content = message.get("content")
        return content if isinstance(content, str) else ""

    @staticmethod
    def _top_logprobs_raw(data: dict[str, Any]) -> list[dict]:
        message = data.get("message")
        candidates = message.get("logprobs") if isinstance(message, dict) else None
        if not isinstance(candidates, list):
            candidates = data.get("logprobs")
        if not isinstance(candidates, list):
            return []
        return [candidate for candidate in candidates if isinstance(candidate, dict)]
