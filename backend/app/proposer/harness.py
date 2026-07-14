import json
import re
from collections.abc import Callable
from typing import Any

from app.proposer.clients import ProposerClient
from app.proposer.prompts import build_infill_messages, build_proposer_messages
from app.strategies.base import ProposedEdit


class ProposerHarness:
    """Builds proposer prompts, calls the proposer client, and counts round-trips."""

    def __init__(
        self,
        *,
        client: ProposerClient,
        original_answer: str,
        temperature: float,
        seed: int,
        num_predict: int,
        on_call: Callable[[], None],
    ) -> None:
        self._client = client
        self._original_answer = original_answer
        self._temperature = temperature
        self._seed = seed
        self._num_predict = num_predict
        self._on_call = on_call

    def propose(
        self,
        scenario: str,
        choices: dict[str, str],
        foil: str,
        count: int,
        avoid: list[str] | None = None,
    ) -> list[ProposedEdit]:
        messages = build_proposer_messages(
            scenario=scenario,
            choices=choices,
            foil=foil,
            original_answer=self._original_answer,
            count=count,
            avoid=avoid,
        )
        return self._complete(messages, count=count)

    def infill(
        self,
        original_scenario: str,
        masked_scenario: str,
        choices: dict[str, str],
        foil: str,
        count: int,
        avoid: list[str] | None = None,
    ) -> list[ProposedEdit]:
        messages = build_infill_messages(
            original_scenario=original_scenario,
            masked_scenario=masked_scenario,
            choices=choices,
            foil=foil,
            original_answer=self._original_answer,
            count=count,
            avoid=avoid,
        )
        return self._complete(messages, count=count)

    def _complete(self, messages: list[dict[str, str]], *, count: int) -> list[ProposedEdit]:
        options = {
            "temperature": self._temperature,
            "seed": self._seed,
            "num_predict": self._num_predict,
        }
        try:
            raw = self._client.complete(messages, options)
        finally:
            self._on_call()
        return parse_proposed_edits(raw, limit=count)


def parse_proposed_edits(raw: str, *, limit: int) -> list[ProposedEdit]:
    if limit <= 0:
        return []
    payload = _load_json_payload(raw)
    if payload is None:
        return []

    items = payload.get("rewrites") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return []

    edits: list[ProposedEdit] = []
    for item in items:
        edit = _coerce_edit(item)
        if edit is None:
            continue
        edits.append(edit)
        if len(edits) >= limit:
            break
    return edits


def _load_json_payload(raw: str) -> Any | None:
    text = _strip_code_fence(raw.strip())
    for candidate in _json_candidates(text):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _strip_code_fence(value: str) -> str:
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", value, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else value


def _json_candidates(value: str) -> list[str]:
    candidates = [value]
    for opening, closing in (("{", "}"), ("[", "]")):
        start = value.find(opening)
        end = value.rfind(closing)
        if start != -1 and end != -1 and end > start:
            candidates.append(value[start : end + 1])
    return candidates


def _coerce_edit(item: Any) -> ProposedEdit | None:
    if isinstance(item, str):
        modified_scenario = item.strip()
        rationale = None
    elif isinstance(item, dict):
        modified = item.get("modified_scenario") or item.get("scenario") or item.get("rewrite")
        if not isinstance(modified, str):
            return None
        modified_scenario = modified.strip()
        raw_rationale = item.get("rationale")
        rationale = raw_rationale.strip() if isinstance(raw_rationale, str) else None
    else:
        return None

    if not modified_scenario:
        return None
    return ProposedEdit(modified_scenario=modified_scenario, rationale=rationale)
