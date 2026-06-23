"""Normalisation and hashing helpers shared by the prediction cache and loaders.

Keeping these in one place guarantees that the prediction cache key, the
``scenario_hash``/``choices_hash`` columns and the EmoBench loader all normalise
text the same way (otherwise the cache would silently miss).
"""

import hashlib
import json


def normalize_scenario(scenario: str) -> str:
    return " ".join(scenario.split())


def normalize_choices_json(choices: dict[str, str]) -> str:
    return json.dumps(choices, sort_keys=True, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def scenario_hash(scenario: str) -> str:
    return _sha256(normalize_scenario(scenario))


def choices_hash(choices: dict[str, str]) -> str:
    return _sha256(normalize_choices_json(choices))


def prediction_cache_key(
    *,
    model: str,
    prompt_template_version: str,
    scenario: str,
    choices: dict[str, str],
) -> str:
    payload = "|".join(
        [
            model,
            prompt_template_version,
            normalize_scenario(scenario),
            normalize_choices_json(choices),
        ]
    )
    return _sha256(payload)
