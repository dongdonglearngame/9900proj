from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Literal

from app.proposer.clients import ProposerClient, ProposerCompletion
from app.proposer.concept_parser import (
    ConceptEditParseResult,
    parse_concept_edits_with_diagnostics,
)
from app.proposer.concept_prompts import (
    S6_CONCEPT_PROMPT_VERSION,
    S6_CONCEPT_REPAIR_PROMPT_VERSION,
    build_concept_proposer_messages,
    build_concept_repair_messages,
)
from app.proposer.json_utils import load_json_payload
from app.proposer.prompts import (
    S2_DEFAULT_PROMPT_VARIANT,
    S4_INFILL_PROMPT_VERSION,
    S2PromptVariant,
    build_infill_messages,
    build_proposer_messages,
    s2_prompt_version,
)
from app.schemas.proposer import ProposerCallDiagnostics
from app.strategies.base import ConceptEdit, ConceptEditKey, ProposedEdit

CandidateOutcome = Literal[
    "unique_valid",
    "target_verified",
    "empty_or_duplicate",
    "foil_leak",
    "changed_fraction",
    "changed_word_limit",
    "sentence_structure",
    "constraint_violation",
    "invalid_span",
    "semantic_evaluative_cue_only",
    "semantic_near_synonym_only",
    "sentence_anchor",
]


@dataclass(frozen=True)
class ProposedEditParseResult:
    edits: list[ProposedEdit]
    raw_candidates: int
    parsed_candidates: int
    invalid_span_candidates: int = 0


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
        s2_prompt_variant: S2PromptVariant = S2_DEFAULT_PROMPT_VARIANT,
        on_diagnostics: Callable[[ProposerCallDiagnostics], None] | None = None,
        on_candidate_outcome: Callable[[CandidateOutcome], None] | None = None,
        on_semantic_risk: Callable[[str], None] | None = None,
    ) -> None:
        self._client = client
        self._original_answer = original_answer
        self._temperature = temperature
        self._seed = seed
        self._num_predict = num_predict
        self._s2_prompt_variant = s2_prompt_variant
        self._call_index = 0
        self._on_call = on_call
        self._on_diagnostics = on_diagnostics
        self._on_candidate_outcome = on_candidate_outcome
        self._on_semantic_risk = on_semantic_risk

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
            variant=self._s2_prompt_variant,
        )
        return self._complete(
            messages,
            count=count,
            prompt_version=s2_prompt_version(self._s2_prompt_variant),
            source_scenario=scenario,
            require_grounded_spans=(self._s2_prompt_variant == "span_grounded"),
        )

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
        return self._complete(
            messages,
            count=count,
            prompt_version=S4_INFILL_PROMPT_VERSION,
        )

    def _complete(
        self,
        messages: list[dict[str, str]],
        *,
        count: int,
        prompt_version: str,
        source_scenario: str | None = None,
        require_grounded_spans: bool = False,
    ) -> list[ProposedEdit]:
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
                source_scenario=source_scenario,
                require_grounded_spans=require_grounded_spans,
            )
            return parse_result.edits
        finally:
            latency_seconds = round(perf_counter() - started, 4)
            self._on_call()
            if self._on_diagnostics is not None:
                self._on_diagnostics(
                    ProposerCallDiagnostics(
                        prompt_version=prompt_version,
                        requested_candidates=count,
                        seed=call_seed,
                        num_predict=self._num_predict,
                        temperature=self._temperature,
                        raw_candidates=parse_result.raw_candidates,
                        parsed_candidates=parse_result.parsed_candidates,
                        delivered_candidates=len(parse_result.edits),
                        invalid_span_candidates=parse_result.invalid_span_candidates,
                        done_reason=(completion.done_reason if completion else "error"),
                        eval_count=completion.eval_count if completion else None,
                        response_tokens=(completion.response_tokens if completion else None),
                        latency_seconds=latency_seconds,
                    )
                )

    def record_candidate_outcome(self, outcome: CandidateOutcome) -> None:
        if self._on_candidate_outcome is not None:
            self._on_candidate_outcome(outcome)

    def record_semantic_risk(self, risk: str) -> None:
        if self._on_semantic_risk is not None:
            self._on_semantic_risk(risk)

    def propose_concept_edits(
        self,
        scenario: str,
        choices: dict[str, str],
        foil: str,
        count: int,
        allowed_concepts: tuple[str, ...],
        avoid: list[str] | None = None,
        used_edits: list[ConceptEditKey] | None = None,
    ) -> list[ConceptEdit]:
        messages = build_concept_proposer_messages(
            scenario=scenario,
            choices=choices,
            foil=foil,
            original_answer=self._original_answer,
            count=count,
            allowed_concepts=allowed_concepts,
            avoid=avoid,
            used_edits=used_edits,
        )
        return self._complete_concepts(
            messages,
            count=count,
            allowed_concepts=allowed_concepts,
            prompt_version=S6_CONCEPT_PROMPT_VERSION,
        )

    def repair_concept_edit(
        self,
        scenario: str,
        choices: dict[str, str],
        foil: str,
        edit: ConceptEdit,
        allowed_concepts: tuple[str, ...],
        used_edits: list[ConceptEditKey] | None = None,
    ) -> ConceptEdit | None:
        messages = build_concept_repair_messages(
            scenario=scenario,
            choices=choices,
            foil=foil,
            original_answer=self._original_answer,
            edit=edit,
            allowed_concepts=allowed_concepts,
            used_edits=used_edits,
        )
        edits = self._complete_concepts(
            messages,
            count=1,
            allowed_concepts=allowed_concepts,
            prompt_version=S6_CONCEPT_REPAIR_PROMPT_VERSION,
        )
        return edits[0] if edits else None

    def _complete_concepts(
        self,
        messages: list[dict[str, str]],
        *,
        count: int,
        allowed_concepts: tuple[str, ...],
        prompt_version: str,
    ) -> list[ConceptEdit]:
        call_seed = self._seed + self._call_index
        self._call_index += 1
        options = {
            "temperature": self._temperature,
            "seed": call_seed,
            "num_predict": self._num_predict,
        }
        started = perf_counter()
        completion: ProposerCompletion | None = None
        parse_result = ConceptEditParseResult([], 0, 0)
        try:
            completion = _normalise_completion(self._client.complete(messages, options))
            parse_result = parse_concept_edits_with_diagnostics(
                completion.content,
                limit=count,
                allowed_concepts=allowed_concepts,
            )
            return parse_result.edits
        finally:
            latency_seconds = round(perf_counter() - started, 4)
            self._on_call()
            if self._on_diagnostics is not None:
                self._on_diagnostics(
                    ProposerCallDiagnostics(
                        prompt_version=prompt_version,
                        requested_candidates=count,
                        seed=call_seed,
                        num_predict=self._num_predict,
                        temperature=self._temperature,
                        raw_candidates=parse_result.raw_candidates,
                        parsed_candidates=parse_result.parsed_candidates,
                        delivered_candidates=len(parse_result.edits),
                        invalid_span_candidates=0,
                        done_reason=(completion.done_reason if completion else "error"),
                        eval_count=completion.eval_count if completion else None,
                        response_tokens=(completion.response_tokens if completion else None),
                        latency_seconds=latency_seconds,
                    )
                )


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
    source_scenario: str | None = None,
    require_grounded_spans: bool = False,
) -> ProposedEditParseResult:
    if limit <= 0:
        return ProposedEditParseResult([], 0, 0)
    raw_text = raw.content if isinstance(raw, ProposerCompletion) else raw
    payload = load_json_payload(raw_text)
    if payload is None:
        return ProposedEditParseResult([], 0, 0)

    items = payload.get("rewrites") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return ProposedEditParseResult([], 0, 0)

    parsed_edits: list[ProposedEdit] = []
    invalid_span_candidates = 0
    for item in items:
        edit, invalid_span = _coerce_edit(
            item,
            source_scenario=source_scenario,
            require_grounded_spans=require_grounded_spans,
        )
        if invalid_span:
            invalid_span_candidates += 1
        if edit is None:
            continue
        parsed_edits.append(edit)
    return ProposedEditParseResult(
        edits=parsed_edits[:limit],
        raw_candidates=len(items),
        parsed_candidates=len(parsed_edits),
        invalid_span_candidates=invalid_span_candidates,
    )


def _coerce_edit(
    item: Any,
    *,
    source_scenario: str | None,
    require_grounded_spans: bool,
) -> tuple[ProposedEdit | None, bool]:
    if isinstance(item, str):
        if require_grounded_spans:
            return None, False
        modified_scenario = item.strip()
        rationale = None
        original_span = None
        replacement_span = None
    elif isinstance(item, dict):
        raw_rationale = item.get("rationale")
        rationale = raw_rationale.strip() if isinstance(raw_rationale, str) else None
        changed_span = _optional_string(item.get("changed_span"))
        change_type = _optional_string(item.get("change_type"))
        original_span = _optional_string(item.get("original_span"))
        replacement_span = _optional_string(item.get("replacement_span"))
        if require_grounded_spans:
            if source_scenario is None or original_span is None or replacement_span is None:
                return None, False
            if (
                source_scenario.count(original_span) != 1
                or original_span == replacement_span
            ):
                return None, True
            modified_scenario = source_scenario.replace(
                original_span,
                replacement_span,
                1,
            )
        else:
            modified = (
                item.get("modified_scenario")
                or item.get("scenario")
                or item.get("rewrite")
            )
            if not isinstance(modified, str):
                return None, False
            modified_scenario = modified.strip()
    else:
        return None, False

    if not modified_scenario:
        return None, False
    if isinstance(item, str):
        changed_span = None
        change_type = None
    return (
        ProposedEdit(
            modified_scenario=modified_scenario,
            rationale=rationale,
            changed_span=changed_span,
            change_type=change_type,
            original_span=original_span,
            replacement_span=replacement_span,
        ),
        False,
    )


def record_candidate_outcome(proposer: object, outcome: CandidateOutcome) -> None:
    recorder = getattr(proposer, "record_candidate_outcome", None)
    if callable(recorder):
        recorder(outcome)


def record_semantic_risk(proposer: object, risk: str) -> None:
    recorder = getattr(proposer, "record_semantic_risk", None)
    if callable(recorder):
        recorder(risk)


def _normalise_completion(value: ProposerCompletion | str) -> ProposerCompletion:
    # String support keeps simple duck-typed test clients and external adapters working.
    return value if isinstance(value, ProposerCompletion) else ProposerCompletion(content=value)


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
