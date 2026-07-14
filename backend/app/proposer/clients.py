import json
import re
from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass(frozen=True)
class ProposerCompletion:
    content: str
    done_reason: str | None = None
    eval_count: int | None = None

    @property
    def response_tokens(self) -> int | None:
        # Ollama reports generated response tokens as eval_count.
        return self.eval_count


class ProposerClient(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        options: dict,
    ) -> ProposerCompletion:
        """Run one generative round-trip and retain response diagnostics."""


class MockProposerClient:
    """Deterministic proposer used by mock mode and tests."""

    def complete(
        self,
        messages: list[dict[str, str]],
        options: dict,
    ) -> ProposerCompletion:
        _ = options
        payload = _payload_from_messages(messages)
        count = max(0, int(payload.get("count", 1)))
        masked_scenario = payload.get("masked_scenario")

        if isinstance(masked_scenario, str):
            candidates = _mock_infill_candidates(masked_scenario)[:count]
            rationale = "mock proposer constrained infill"
        else:
            scenario = payload.get("scenario", "")
            candidates = _mock_candidates(str(scenario))[:count]
            rationale = "mock proposer minimal time shift"
        rewrites = [
            {"modified_scenario": candidate, "rationale": rationale}
            for candidate in candidates
        ]
        return ProposerCompletion(
            content=json.dumps({"rewrites": rewrites}),
            done_reason="stop",
        )


class OllamaProposerClient:
    """Generative proposer client, separate from the frozen target client."""

    def __init__(self, *, base_url: str, model: str, timeout: float = 120) -> None:
        self._base_url = base_url
        self._model = model
        self._timeout = timeout

    def complete(
        self,
        messages: list[dict[str, str]],
        options: dict,
    ) -> ProposerCompletion:
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "keep_alive": "10m",
            "options": options,
        }
        response = httpx.post(
            f"{self._base_url}/api/chat",
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        message = data.get("message")
        if not isinstance(message, dict):
            return ProposerCompletion(
                content="",
                done_reason=_optional_string(data.get("done_reason")),
                eval_count=_optional_int(data.get("eval_count")),
            )
        content = message.get("content")
        return ProposerCompletion(
            content=content if isinstance(content, str) else "",
            done_reason=_optional_string(data.get("done_reason")),
            eval_count=_optional_int(data.get("eval_count")),
        )


def _payload_from_messages(messages: list[dict[str, str]]) -> dict:
    if not messages:
        return {}
    try:
        return json.loads(messages[-1].get("content", "{}"))
    except json.JSONDecodeError:
        return {}


def _mock_candidates(scenario: str) -> list[str]:
    replacements = (
        ("middle of the night", "early evening"),
        ("late at night", "early evening"),
        ("after midnight", "early evening"),
        ("overnight", "during the afternoon"),
    )
    lower = scenario.lower()
    candidates: list[str] = []

    for source, replacement in replacements:
        index = lower.find(source)
        if index == -1:
            continue
        original = scenario[index : index + len(source)]
        candidates.append(
            _replace_span(scenario, index, index + len(source), original, replacement)
        )

    if "early evening" not in lower and "afternoon" not in lower:
        stripped = scenario.strip()
        if stripped:
            candidates.append(f"{stripped} It is early evening.")

    return _dedupe_preserving_order(candidates)


def _mock_infill_candidates(masked_scenario: str) -> list[str]:
    if "[MASK]" not in masked_scenario:
        return []

    fills = ("early evening", "afternoon", "during the afternoon")
    return _dedupe_preserving_order(
        [masked_scenario.replace("[MASK]", fill) for fill in fills]
    )


def _replace_span(
    scenario: str,
    start: int,
    end: int,
    original: str,
    replacement: str,
) -> str:
    if original[:1].isupper():
        replacement = replacement[:1].upper() + replacement[1:]
    return f"{scenario[:start]}{replacement}{scenario[end:]}"


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = re.sub(r"\s+", " ", value).strip().casefold()
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
