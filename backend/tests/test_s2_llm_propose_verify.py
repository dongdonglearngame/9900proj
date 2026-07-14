from fastapi.testclient import TestClient

from app.harness.target_predict import PredictionResult
from app.main import app
from app.strategies.base import ProposedEdit
from app.strategies.s2_llm_propose_verify import S2LlmProposeVerifyStrategy

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
        option_logprobs={"A": -2.0 if answer == "C" else -0.1, "B": None, "C": -0.1, "D": None},
        option_probs={"A": 0.1 if answer == "C" else 0.8, "B": None, "C": 0.8, "D": None},
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


class FakeProposer:
    def __init__(self, rounds: list[list[ProposedEdit]]) -> None:
        self.rounds = rounds
        self.calls = 0
        self.count_history: list[int] = []
        self.avoid_history: list[list[str] | None] = []

    def propose(
        self,
        scenario: str,
        choices: dict[str, str],
        foil: str,
        count: int,
        avoid: list[str] | None = None,
    ) -> list[ProposedEdit]:
        _ = scenario
        _ = choices
        _ = foil
        self.count_history.append(count)
        self.avoid_history.append(avoid)
        index = self.calls
        self.calls += 1
        return self.rounds[index] if index < len(self.rounds) else []


def edit(scenario: str, rationale: str = "test edit") -> ProposedEdit:
    return ProposedEdit(modified_scenario=scenario, rationale=rationale)


def test_s2_success_path_records_rationale() -> None:
    proposer = FakeProposer(
        [[edit(REGINA_SCENARIO.replace("middle of the night", "early evening"), "time shift")]]
    )
    target = FakeTargetModel()

    result = S2LlmProposeVerifyStrategy(max_rounds=2, candidates_per_round=4).generate(
        scenario=REGINA_SCENARIO,
        choices=CHOICES,
        model=target,
        foil="C",
        budget=5,
        proposer=proposer,
    )

    assert result.status == "success"
    assert result.new_answer == "C"
    assert result.modified_scenario is not None
    assert "early evening" in result.modified_scenario
    assert result.attempts[0].edit_description == "time shift"
    assert proposer.calls == 1
    assert len(target.calls) == 1


def test_s2_not_found_when_verified_candidates_do_not_flip() -> None:
    proposer = FakeProposer(
        [[edit(REGINA_SCENARIO.replace("middle of the night", "early morning"))]]
    )
    target = FakeTargetModel()

    result = S2LlmProposeVerifyStrategy(max_rounds=1, candidates_per_round=4).generate(
        scenario=REGINA_SCENARIO,
        choices=CHOICES,
        model=target,
        foil="C",
        budget=5,
        proposer=proposer,
    )

    assert result.status == "not_found"
    assert result.new_answer is None
    assert len(result.attempts) == 1
    assert len(target.calls) == 1


def test_s2_never_exceeds_target_budget_when_proposer_overgenerates() -> None:
    proposer = FakeProposer(
        [
            [
                edit(REGINA_SCENARIO.replace("middle of the night", "early morning")),
                edit(REGINA_SCENARIO.replace("middle of the night", "late morning")),
                edit(REGINA_SCENARIO.replace("middle of the night", "after breakfast")),
                edit(REGINA_SCENARIO.replace("middle of the night", "before lunch")),
            ]
        ]
    )
    target = FakeTargetModel(flip_token="will not flip")

    result = S2LlmProposeVerifyStrategy(max_rounds=1, candidates_per_round=10).generate(
        scenario=REGINA_SCENARIO,
        choices=CHOICES,
        model=target,
        foil="C",
        budget=2,
        proposer=proposer,
    )

    assert result.status == "not_found"
    assert len(result.attempts) == 2
    assert len(target.calls) == 2


def test_s2_rejects_foil_text_leak_before_target_verification() -> None:
    proposer = FakeProposer([[edit(f"Regina should {CHOICES['C']}.")]])
    target = FakeTargetModel()

    result = S2LlmProposeVerifyStrategy(max_rounds=1, candidates_per_round=4).generate(
        scenario=REGINA_SCENARIO,
        choices=CHOICES,
        model=target,
        foil="C",
        budget=5,
        proposer=proposer,
    )

    assert result.status == "not_found"
    assert result.attempts == []
    assert target.calls == []


def test_s2_rejects_morphological_foil_leak_before_target_verification() -> None:
    choices = {**CHOICES, "C": "relief"}
    proposer = FakeProposer([[edit("Regina felt relieved after hearing the news.")]])
    target = FakeTargetModel()

    result = S2LlmProposeVerifyStrategy(max_rounds=1, candidates_per_round=2).generate(
        scenario="Regina heard the news and considered what it meant.",
        choices=choices,
        model=target,
        foil="C",
        budget=2,
        proposer=proposer,
    )

    assert result.status == "not_found"
    assert result.attempts == []
    assert target.calls == []


def test_s2_skips_oversized_rewrites_without_target_call() -> None:
    long_rewrite = " ".join(f"new{i}" for i in range(40))
    proposer = FakeProposer([[edit(long_rewrite)]])
    target = FakeTargetModel()

    result = S2LlmProposeVerifyStrategy(
        max_rounds=1,
        candidates_per_round=4,
        max_changed_fraction=0.1,
    ).generate(
        scenario="short scenario",
        choices=CHOICES,
        model=target,
        foil="C",
        budget=5,
        proposer=proposer,
    )

    assert result.status == "not_found"
    assert result.attempts == []
    assert target.calls == []


def test_s2_dedupes_across_rounds_and_passes_avoid_rejects() -> None:
    first = REGINA_SCENARIO.replace("middle of the night", "early morning")
    duplicate = f"  {first.lower()}  "
    second = REGINA_SCENARIO.replace("middle of the night", "early evening")
    proposer = FakeProposer([[edit(first)], [edit(duplicate), edit(second)]])
    target = FakeTargetModel()

    result = S2LlmProposeVerifyStrategy(max_rounds=2, candidates_per_round=4).generate(
        scenario=REGINA_SCENARIO,
        choices=CHOICES,
        model=target,
        foil="C",
        budget=5,
        proposer=proposer,
    )

    assert result.status == "success"
    assert proposer.calls == 2
    assert proposer.avoid_history[1] == [f"target_answer=A: {first}"]
    assert target.calls == [first, second]


def test_s2_refills_after_proposer_under_delivers() -> None:
    first = REGINA_SCENARIO.replace("middle of the night", "early morning")
    second = REGINA_SCENARIO.replace("middle of the night", "late morning")
    proposer = FakeProposer([[edit(first)], [edit(second)]])
    target = FakeTargetModel(flip_token="will not flip")

    result = S2LlmProposeVerifyStrategy(max_rounds=2, candidates_per_round=4).generate(
        scenario=REGINA_SCENARIO,
        choices=CHOICES,
        model=target,
        foil="C",
        budget=4,
        proposer=proposer,
    )

    assert result.status == "not_found"
    assert proposer.calls == 2
    assert proposer.count_history == [4, 3]
    assert target.calls == [first, second]


def test_s2_ranks_minimal_candidate_before_larger_rewrite() -> None:
    larger = REGINA_SCENARIO.replace(
        "middle of the night",
        "early morning after a long and difficult journey",
    )
    minimal = REGINA_SCENARIO.replace("middle of the night", "early morning")
    proposer = FakeProposer([[edit(larger), edit(minimal)]])
    target = FakeTargetModel(flip_token="will not flip")

    result = S2LlmProposeVerifyStrategy(max_rounds=1, candidates_per_round=2).generate(
        scenario=REGINA_SCENARIO,
        choices=CHOICES,
        model=target,
        foil="C",
        budget=2,
        proposer=proposer,
    )

    assert result.status == "not_found"
    assert target.calls == [minimal, larger]


def test_counterfactual_api_runs_s2_in_mock_mode() -> None:
    client = TestClient(app)

    created = client.post(
        "/counterfactual",
        json={
            "question_id": "q_regina_s2",
            "scenario": REGINA_SCENARIO,
            "choices": CHOICES,
            "model": "mock",
            "original_answer": "A",
            "foil": "C",
            "strategy_id": "s2_llm_propose_verify",
            "budget": 5,
        },
    ).json()
    job = client.get(f"/counterfactual/jobs/{created['job_id']}").json()

    assert job["status"] == "completed"
    assert job["result"]["status"] == "success"
    assert job["result"]["new_answer"] == "C"
    assert job["progress"]["proposer_calls"] == 1
    assert job["result"]["metrics"]["proposer_calls"] == 1
    assert job["result"]["metrics"]["search_calls"] == 1
    diagnostics = job["result"]["proposer_diagnostics"]
    assert diagnostics["requested_candidates"] == 4
    assert diagnostics["raw_candidates"] == 2
    assert diagnostics["parsed_candidates"] == 2
    assert diagnostics["unique_valid_candidates"] == 2
    assert diagnostics["target_verified_candidates"] == 1
    assert diagnostics["raw_requested_yield"] == 0.5
    assert diagnostics["target_verified_parsed_yield"] == 0.5
    assert diagnostics["calls"][0]["done_reason"] == "stop"
    assert diagnostics["calls"][0]["num_predict"] == 1024
    assert diagnostics["calls"][0]["prompt_version"] == (
        "s2-proposer-v2-event-grounded"
    )
    metrics = job["result"]["metrics"]
    assert metrics["foil_logprob_delta"] == 1.7
    assert metrics["mean_foil_logprob_delta"] == 1.7
    assert metrics["max_foil_logprob_delta"] == 1.7
    assert metrics["positive_delta_rate"] == 1.0
    assert metrics["logprob_coverage"] == 1.0
