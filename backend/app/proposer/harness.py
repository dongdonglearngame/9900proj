import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Literal

from app.proposer.clients import ProposerClient, ProposerCompletion
from app.proposer.prompts import build_infill_messages, build_proposer_messages
from app.schemas.proposer import ProposerCallDiagnostics
from app.strategies.base import ProposedEdit

CandidateOutcome = Literal[
    "unique_valid",
    "target_verified",
    "empty_or_duplicate",
    "foil_leak",
    "changed_fraction",
    "constraint_violation",
    "invalid_span",
]


@dataclass(frozen=True)
class ProposedEditParseResult:
    edits: list[ProposedEdit]
    raw_candidates: int
    parsed_candidates: int


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
        on_diagnostics: Callable[[ProposerCallDiagnostics], None] | None = None,
        on_candidate_outcome: Callable[[CandidateOutcome], None] | None = None,
    ) -> None:
        self._client = client
        self._original_answer = original_answer
        self._temperature = temperature
        self._seed = seed
        self._num_predict = num_predict
        self._call_index = 0
        self._on_call = on_call
        self._on_diagnostics = on_diagnostics
        self._on_candidate_outcome = on_candidate_outcome

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
        call_seed = self._seed + self._call_index
        self._call_index += 1
        options = {
            "temperature": self._temperature,
            "seed": call_seed,
            "num_predict": self._num_predict,
        }
        started = perf_counter()
        completion: ProposerCompletion | None = None
        parse_result = ProposedEditParseResult([], 0, 0)
        try:
            completion = _normalise_completion(self._client.complete(messages, options))
            parse_result = parse_proposed_edits_with_diagnostics(
                completion.content,
                limit=count,
            )
            return parse_result.edits
        finally:
            latency_seconds = round(perf_counter() - started, 4)
            self._on_call()
            if self._on_diagnostics is not None:
                self._on_diagnostics(
                    ProposerCallDiagnostics(
                        requested_candidates=count,
                        seed=call_seed,
                        num_predict=self._num_predict,
                        temperature=self._temperature,
                        raw_candidates=parse_result.raw_candidates,
                        parsed_candidates=parse_result.parsed_candidates,
                        delivered_candidates=len(parse_result.edits),
                        done_reason=(completion.done_reason if completion else "error"),
                        eval_count=completion.eval_count if completion else None,
                        response_tokens=(completion.response_tokens if completion else None),
                        latency_seconds=latency_seconds,
                    )
                )

    def record_candidate_outcome(self, outcome: CandidateOutcome) -> None:
        if self._on_candidate_outcome is not None:
            self._on_candidate_outcome(outcome)


def parse_proposed_edits(
    raw: str | ProposerCompletion,
    *,
    limit: int,
) -> list[ProposedEdit]:
    return parse_proposed_edits_with_diagnostics(raw, limit=limit).edits


def parse_proposed_edits_with_diagnostics(
    raw: str | ProposerCompletion,
    *,
    limit: int,
) -> ProposedEditParseResult:
    if limit <= 0:
        return ProposedEditParseResult([], 0, 0)
    raw_text = raw.content if isinstance(raw, ProposerCompletion) else raw
    payload = _load_json_payload(raw_text)
    if payload is None:
        return ProposedEditParseResult([], 0, 0)

    items = payload.get("rewrites") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return ProposedEditParseResult([], 0, 0)

    parsed_edits: list[ProposedEdit] = []
    for item in items:
        edit = _coerce_edit(item)
        if edit is None:
            continue
        parsed_edits.append(edit)
    return ProposedEditParseResult(
        edits=parsed_edits[:limit],
        raw_candidates=len(items),
        parsed_candidates=len(parsed_edits),
    )


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
        changed_span = _optional_string(item.get("changed_span"))
        change_type = _optional_string(item.get("change_type"))
    else:
        return None

    if not modified_scenario:
        return None
    if isinstance(item, str):
        changed_span = None
        change_type = None
    return ProposedEdit(
        modified_scenario=modified_scenario,
        rationale=rationale,
        changed_span=changed_span,
        change_type=change_type,
    )


def record_candidate_outcome(proposer: object, outcome: CandidateOutcome) -> None:
    recorder = getattr(proposer, "record_candidate_outcome", None)
    if callable(recorder):
        recorder(outcome)


def _normalise_completion(value: ProposerCompletion | str) -> ProposerCompletion:
    # String support keeps simple duck-typed test clients and external adapters working.
    return value if isinstance(value, ProposerCompletion) else ProposerCompletion(content=value)


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
