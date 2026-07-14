import json
import re
from typing import Any


def load_json_payload(raw: str) -> Any | None:
    text = _strip_code_fence(raw.strip())
    for candidate in _json_candidates(text):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _strip_code_fence(value: str) -> str:
    match = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(1).strip() if match else value


def _json_candidates(value: str) -> list[str]:
    candidates = [value]
    for opening, closing in (("{", "}"), ("[", "]")):
        start = value.find(opening)
        end = value.rfind(closing)
        if start != -1 and end != -1 and end > start:
            candidates.append(value[start : end + 1])
    return candidates
