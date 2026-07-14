from collections.abc import Callable
from typing import Any

from app.proposer.clients import ProposerClient
from app.proposer.concept_parser import parse_concept_edits
from app.proposer.concept_prompts import build_concept_proposer_messages
from app.proposer.json_utils import load_json_payload
from app.proposer.prompts import build_proposer_messages
from app.strategies.base import ConceptEdit, ProposedEdit


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

    def propose_concept_edits(
        self,
        scenario: str,
        choices: dict[str, str],
        foil: str,
        count: int,
        allowed_concepts: tuple[str, ...],
        avoid: list[str] | None = None,
    ) -> list[ConceptEdit]:
        messages = build_concept_proposer_messages(
            scenario=scenario,
            choices=choices,
            foil=foil,
            original_answer=self._original_answer,
            count=count,
            allowed_concepts=allowed_concepts,
            avoid=avoid,
        )
        options = {
            "temperature": self._temperature,
            "seed": self._seed,
            "num_predict": self._num_predict,
        }
        try:
            raw = self._client.complete(messages, options)
        finally:
            self._on_call()
        return parse_concept_edits(
            raw,
            limit=count,
            allowed_concepts=allowed_concepts,
        )


def parse_proposed_edits(raw: str, *, limit: int) -> list[ProposedEdit]:
    if limit <= 0:
        return []
    payload = load_json_payload(raw)
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
