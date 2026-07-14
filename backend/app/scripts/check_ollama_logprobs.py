import argparse
import json
import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.llm.ollama_client import OllamaClient

MIN_OLLAMA_VERSION = (0, 12, 11)
PREFLIGHT_CHOICES = {
    "A": "Offer calm and practical support",
    "B": "Ignore the situation completely",
}
PREFLIGHT_SCENARIO = (
    "A friend says they feel overwhelmed and asks for help deciding what to do next."
)


def run_preflight(model: str) -> dict[str, Any]:
    settings = get_settings()
    version_url = f"{settings.ollama_base_url.rstrip('/')}/api/version"
    try:
        response = httpx.get(version_url, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"could not query Ollama at {version_url}: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Ollama returned a non-JSON version response") from exc
    version_text = payload.get("version") if isinstance(payload, dict) else None
    version = _parse_version(version_text)
    if version is None:
        raise RuntimeError(f"Ollama returned an invalid version: {version_text!r}")
    if version < MIN_OLLAMA_VERSION:
        minimum = ".".join(str(part) for part in MIN_OLLAMA_VERSION)
        raise RuntimeError(f"Ollama {minimum}+ is required; found {version_text}")

    try:
        prediction = OllamaClient().predict(PREFLIGHT_SCENARIO, PREFLIGHT_CHOICES, model)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"target-model logprob probe failed: {exc}") from exc
    if prediction.status != "ok":
        raise RuntimeError("the frozen target prompt did not return a parseable choice")

    missing = [
        letter
        for letter in PREFLIGHT_CHOICES
        if prediction.option_logprobs.get(letter) is None
    ]
    if missing:
        raise RuntimeError(
            "Ollama did not return option logprobs for: " + ", ".join(missing)
        )

    return {
        "status": "ok",
        "ollama_version": version_text,
        "model": model,
        "answer": prediction.answer,
        "option_logprobs": prediction.option_logprobs,
    }


def _parse_version(value: object) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    match = re.match(r"^\s*(\d+)\.(\d+)\.(\d+)", value)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Check the Ollama version and target-model option logprobs."
    )
    parser.add_argument("--model", default=settings.default_model)
    args = parser.parse_args()

    try:
        result = run_preflight(args.model)
    except RuntimeError as exc:
        raise SystemExit(f"Ollama logprob preflight failed: {exc}") from exc
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
