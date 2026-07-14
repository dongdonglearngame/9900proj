from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.harness.target_predict import PredictionResult
from app.main import app
from app.services.counterfactual_service import _select_publishable_result
from app.strategies.base import AttemptRecord, ConceptEdit, CounterfactualResult
from app.strategies.s6_concept_causal_editing import S6ConceptCausalEditingStrategy

CHOICES = {
    "A": "Ignore the texts and continue sleeping",
    "B": "Tell her friend to seek professional help",
    "C": "Stay up and lend a listening ear",
    "D": "Suggest her friend find a new partner",
}

REGINA_SCENARIO = (
    "Regina's best friend recently broke up with her longtime partner and is "
    "texting Regina in the middle of the night expressing feelings of loneliness."
)


def _prediction(answer: str) -> PredictionResult:
    return PredictionResult(
        status="ok",
        answer=answer,
        answer_text=CHOICES.get(answer),
        model="mock",
        prompt_template_version="test",
        cache_hit=False,
        raw_response=answer,
        option_logprobs={letter: None for letter in CHOICES},
        option_probs={letter: None for letter in CHOICES},
        top_logprobs_raw=[],
        runtime_seconds=0.0,
    )


class FakeTargetModel:
    def __init__(self, *, flip_token: str = "early evening") -> None:
        self.flip_token = flip_token
        self.calls: list[str] = []

    def target_predict(self, scenario: str, choices: dict[str, str]) -> PredictionResult:
        _ = choices
        self.calls.append(scenario)
        return _prediction("C" if self.flip_token in scenario else "A")


class FakeConceptProposer:
    def __init__(self, rounds: list[list[ConceptEdit]]) -> None:
        self.rounds = rounds
        self.calls = 0
        self.avoid_history: list[list[str] | None] = []

    def propose_concept_edits(
        self,
        scenario: str,
        choices: dict[str, str],
        foil: str,
        count: int,
        allowed_concepts: tuple[str, ...],
        avoid: list[str] | None = None,
    ) -> list[ConceptEdit]:
        _ = scenario
        _ = choices
        _ = foil
        _ = count
        _ = allowed_concepts
        self.avoid_history.append(avoid)
        index = self.calls
        self.calls += 1
        return self.rounds[index] if index < len(self.rounds) else []


def concept(
    original_span: str,
    replacement_span: str,
    concept_class: str = "time",
) -> ConceptEdit:
    return ConceptEdit(
        concept_class=concept_class,
        original_span=original_span,
        replacement_span=replacement_span,
        source_value=original_span,
        target_value=replacement_span,
        rationale="test concept intervention",
    )


def test_s6_success_returns_resolved_concept_metadata() -> None:
    proposer = FakeConceptProposer(
        [[concept("MIDDLE OF THE NIGHT", "early evening")]]
    )
    target = FakeTargetModel()

    result = S6ConceptCausalEditingStrategy(max_rounds=2).generate(
        REGINA_SCENARIO,
        CHOICES,
        target,
        "C",
        budget=5,
        proposer=proposer,
    )

    assert result.status == "success"
    assert result.concept_edit is not None
    assert result.concept_edit.original_span == "middle of the night"
    assert result.concept_edit.replacement_span == "early evening"
    assert result.modified_scenario == REGINA_SCENARIO.replace(
        "middle of the night", "early evening"
    )
    assert result.attempts[0].edit_description is not None
    assert result.attempts[0].edit_description.startswith("time:")
    assert len(target.calls) == 1


def test_s6_stops_after_max_rounds_when_all_spans_are_invalid() -> None:
    invalid = concept("span that is absent", "early evening")
    proposer = FakeConceptProposer([[invalid], [invalid], [invalid]])
    target = FakeTargetModel()

    result = S6ConceptCausalEditingStrategy(max_rounds=2).generate(
        REGINA_SCENARIO,
        CHOICES,
        target,
        "C",
        budget=5,
        proposer=proposer,
    )

    assert result.status == "not_found"
    assert proposer.calls == 2
    assert target.calls == []
    assert proposer.avoid_history[1] == [
        "time: 'span that is absent' -> 'early evening'"
    ]


def test_s6_enforces_target_budget_when_proposer_overgenerates() -> None:
    proposer = FakeConceptProposer(
        [
            [
                concept("middle of the night", "early morning"),
                concept("middle of the night", "late morning"),
                concept("middle of the night", "before lunch"),
            ]
        ]
    )
    target = FakeTargetModel(flip_token="will not flip")

    result = S6ConceptCausalEditingStrategy(
        candidates_per_round=10,
        max_rounds=1,
    ).generate(
        REGINA_SCENARIO,
        CHOICES,
        target,
        "C",
        budget=2,
        proposer=proposer,
    )

    assert result.status == "not_found"
    assert len(result.attempts) == 2
    assert len(target.calls) == 2


def test_s6_filters_foil_leak_and_oversized_edit_before_target_call() -> None:
    leak = concept("middle of the night", CHOICES["C"], "emotional_cause")
    oversized = concept("middle of the night", " ".join(f"new{i}" for i in range(40)))
    proposer = FakeConceptProposer([[leak, oversized]])
    target = FakeTargetModel()

    result = S6ConceptCausalEditingStrategy(
        max_rounds=1,
        max_changed_fraction=0.1,
    ).generate(
        REGINA_SCENARIO,
        CHOICES,
        target,
        "C",
        budget=5,
        proposer=proposer,
    )

    assert result.status == "not_found"
    assert result.attempts == []
    assert target.calls == []


def test_s6_dedupes_across_rounds_and_passes_bounded_avoid_history() -> None:
    first = concept("middle of the night", "early morning")
    duplicate = concept("MIDDLE OF THE NIGHT", "early morning")
    success = concept("middle of the night", "early evening")
    proposer = FakeConceptProposer([[first], [duplicate, success]])
    target = FakeTargetModel()

    result = S6ConceptCausalEditingStrategy(max_rounds=2).generate(
        REGINA_SCENARIO,
        CHOICES,
        target,
        "C",
        budget=5,
        proposer=proposer,
    )

    assert result.status == "success"
    assert proposer.avoid_history[1] == [
        "time: 'middle of the night' -> 'early morning'"
    ]
    assert len(target.calls) == 2


def _successful_result(edit: ConceptEdit) -> CounterfactualResult:
    modified = REGINA_SCENARIO.replace(edit.original_span, edit.replacement_span)
    prediction = _prediction("C")
    return CounterfactualResult(
        status="success",
        original_scenario=REGINA_SCENARIO,
        modified_scenario=modified,
        new_answer="C",
        foil="C",
        strategy_id="s6_concept_causal_editing",
        attempts=[AttemptRecord(modified, prediction, True)],
        concept_edit=edit,
    )


def test_invalid_postprocessed_concept_metadata_reverts_to_raw_result() -> None:
    raw = _successful_result(concept("middle of the night", "early evening"))
    processed = replace(raw, modified_scenario=REGINA_SCENARIO.replace("night", "morning"))

    selected = _select_publishable_result(raw, processed)

    assert selected is raw


def test_invalid_raw_concept_metadata_fails_closed() -> None:
    raw = _successful_result(concept("absent span", "early evening"))

    with pytest.raises(ValueError, match="inconsistent concept metadata"):
        _select_publishable_result(raw, raw)


def test_s6_success_without_concept_metadata_fails_closed() -> None:
    result = replace(
        _successful_result(concept("middle of the night", "early evening")),
        concept_edit=None,
    )

    with pytest.raises(ValueError, match="missing required concept metadata"):
        _select_publishable_result(result, result)


def test_counterfactual_api_runs_s6_in_mock_mode() -> None:
    client = TestClient(app)
    created = client.post(
        "/counterfactual",
        json={
            "question_id": "q_regina_s6",
            "scenario": REGINA_SCENARIO,
            "choices": CHOICES,
            "model": "mock",
            "original_answer": "A",
            "foil": "C",
            "strategy_id": "s6_concept_causal_editing",
            "budget": 5,
        },
    ).json()

    job = client.get(f"/counterfactual/jobs/{created['job_id']}").json()

    assert job["status"] == "completed"
    assert job["result"]["status"] == "success"
    assert job["result"]["new_answer"] == "C"
    assert job["result"]["concept_edit"] == {
        "concept_class": "time",
        "original_span": "middle of the night",
        "replacement_span": "early evening",
        "source_value": "late night",
        "target_value": "early evening",
        "rationale": "mock proposer single-concept time shift",
    }
    assert job["progress"]["proposer_calls"] == 1
    assert job["progress"]["search_calls"] == 1
