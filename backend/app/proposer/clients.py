import json
import re
from typing import Protocol

import httpx


class ProposerClient(Protocol):
    def complete(self, messages: list[dict[str, str]], options: dict) -> str:
        """One generative round-trip; returns raw assistant text."""


class MockProposerClient:
    """Deterministic proposer used by mock mode and tests."""

    def complete(self, messages: list[dict[str, str]], options: dict) -> str:
        _ = options
        payload = _payload_from_messages(messages)
        scenario = payload.get("scenario", "")
        count = max(0, int(payload.get("count", 1)))

        if payload.get("mode") == "concept_edit":
            return json.dumps(
                {
                    "edits": _mock_concept_edits(
                        str(scenario),
                        allowed_concepts=payload.get("allowed_concepts", []),
                        avoid=payload.get("avoid", []),
                    )[:count]
                }
            )

        candidates = _mock_candidates(str(scenario))[:count]
        rewrites = [
            {"modified_scenario": candidate, "rationale": "mock proposer minimal time shift"}
            for candidate in candidates
        ]
        return json.dumps({"rewrites": rewrites})


class OllamaProposerClient:
    """Generative proposer client, separate from the frozen target client."""

    def __init__(self, *, base_url: str, model: str, timeout: float = 120) -> None:
        self._base_url = base_url
        self._model = model
        self._timeout = timeout

    def complete(self, messages: list[dict[str, str]], options: dict) -> str:
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
            return ""
        content = message.get("content")
        return content if isinstance(content, str) else ""


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


def _mock_concept_edits(
    scenario: str,
    *,
    allowed_concepts: object,
    avoid: object,
) -> list[dict[str, str]]:
    if not isinstance(allowed_concepts, list) or "time" not in allowed_concepts:
        return []
    avoided = (
        {value for value in avoid if isinstance(value, str)}
        if isinstance(avoid, list)
        else set()
    )
    replacements = (
        ("middle of the night", "early evening"),
        ("late at night", "early evening"),
        ("after midnight", "early evening"),
        ("overnight", "during the afternoon"),
    )
    lower = scenario.casefold()
    edits: list[dict[str, str]] = []
    for source, replacement in replacements:
        index = lower.find(source)
        if index == -1:
            continue
        original = scenario[index : index + len(source)]
        description = f"time: '{original}' -> '{replacement}'"
        if description in avoided:
            continue
        edits.append(
            {
                "concept_class": "time",
                "original_span": original,
                "replacement_span": replacement,
                "source_value": "late night",
                "target_value": "early evening",
                "rationale": "mock proposer single-concept time shift",
            }
        )
    return edits


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
