from math import exp
from typing import Any

from app.harness.target_predict import ChoiceLetter

CHOICES: tuple[ChoiceLetter, ...] = ("A", "B", "C", "D")


def normalize_token(token: str) -> str:
    return token.strip().upper()


def empty_option_scores() -> dict[ChoiceLetter, float | None]:
    return {letter: None for letter in CHOICES}


def extract_option_logprobs(payload: dict[str, Any]) -> dict[ChoiceLetter, float | None]:
    scores = empty_option_scores()
    for candidates in _iter_top_logprob_candidates(payload):
        for candidate in candidates:
            token = normalize_token(str(candidate.get("token", "")))
            if token not in scores:
                continue

            logprob = candidate.get("logprob")
            if isinstance(logprob, bool) or not isinstance(logprob, int | float):
                continue

            current = scores[token]
            scores[token] = float(logprob) if current is None else max(current, float(logprob))

        if any(value is not None for value in scores.values()):
            break

    return scores


def option_logprobs_to_probs(
    option_logprobs: dict[ChoiceLetter, float | None],
) -> dict[ChoiceLetter, float | None]:
    return {
        letter: round(exp(value), 6) if value is not None else None
        for letter, value in option_logprobs.items()
    }


def _iter_top_logprob_candidates(payload: dict[str, Any]) -> list[list[dict[str, Any]]]:
    direct = payload.get("logprobs")
    if isinstance(direct, list):
        return [_coerce_candidates(item) for item in direct]

    message = payload.get("message")
    if isinstance(message, dict):
        message_logprobs = message.get("logprobs")
        if isinstance(message_logprobs, list):
            return [_coerce_candidates(item) for item in message_logprobs]

    return []


def _coerce_candidates(item: Any) -> list[dict[str, Any]]:
    if isinstance(item, dict):
        candidates = item.get(
            "top_logprobs",
            item.get("top_logprobs_raw", item.get("candidates", [])),
        )
        if isinstance(candidates, list):
            return [candidate for candidate in candidates if isinstance(candidate, dict)]

    if isinstance(item, list):
        return [candidate for candidate in item if isinstance(candidate, dict)]

    return []
