from app.harness.target_predict import PredictionResult
from app.strategies.base import ProposedEdit
from app.strategies.s4_importance_infilling import S4ImportanceInfillingStrategy

CHOICES = {
    "A": "Ignore the texts and continue sleeping",
    "B": "Tell her friend to seek professional help",
    "C": "Stay up and lend a listening ear",
    "D": "Suggest her friend find a new partner",
}


def _prediction(
    answer: str,
    *,
    a_logprob: float | None = -0.1,
    c_logprob: float | None = -2.0,
) -> PredictionResult:
    return PredictionResult(
        status="ok",
        answer=answer,
        answer_text=CHOICES.get(answer),
        model="mock",
        prompt_template_version="test",
        cache_hit=False,
        raw_response=answer,
        option_logprobs={"A": a_logprob, "B": None, "C": c_logprob, "D": None},
        option_probs={"A": None, "B": None, "C": None, "D": None},
        top_logprobs_raw=[],
        runtime_seconds=0.0,
    )


class ImportanceTarget:
    def __init__(self, *, use_logprobs: bool = True) -> None:
        self.calls: list[str] = []
        self.use_logprobs = use_logprobs

    def target_predict(self, scenario: str, choices: dict[str, str]) -> PredictionResult:
        _ = choices
        self.calls.append(scenario)
        lower = scenario.lower()
        if "early evening" in lower:
            return _prediction("C", a_logprob=-2.2, c_logprob=-0.2)
        if "night" not in lower:
            if self.use_logprobs:
                return _prediction("B", a_logprob=-1.4, c_logprob=-0.7)
            return _prediction("B", a_logprob=None, c_logprob=None)
        if "middle" not in lower:
            if self.use_logprobs:
                return _prediction("A", a_logprob=-0.6, c_logprob=-1.5)
            return _prediction("A", a_logprob=None, c_logprob=None)
        if self.use_logprobs:
            return _prediction("A", a_logprob=-0.1, c_logprob=-2.0)
        return _prediction("A", a_logprob=None, c_logprob=None)


class TwoSpanTarget:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def target_predict(self, scenario: str, choices: dict[str, str]) -> PredictionResult:
        _ = choices
        self.calls.append(scenario)
        lower = scenario.lower()
        if "calm early evening" in lower:
            return _prediction("C", a_logprob=-2.5, c_logprob=-0.2)
        if "lonely" not in lower:
            return _prediction("B", a_logprob=-1.6, c_logprob=-0.9)
        if "night" not in lower:
            return _prediction("B", a_logprob=-1.3, c_logprob=-1.0)
        return _prediction("A", a_logprob=-0.1, c_logprob=-2.0)


class NonFlippingTarget:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def target_predict(self, scenario: str, choices: dict[str, str]) -> PredictionResult:
        _ = choices
        self.calls.append(scenario)
        if "night" not in scenario.lower():
            return _prediction("B", a_logprob=-1.0, c_logprob=-1.0)
        return _prediction("A")


class FakeInfillProposer:
    def __init__(self, rounds: list[list[ProposedEdit]] | None = None) -> None:
        self.rounds = rounds
        self.infill_calls: list[str] = []
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
        _ = count
        _ = avoid
        raise AssertionError("S4 must use proposer.infill, not proposer.propose")

    def infill(
        self,
        original_scenario: str,
        masked_scenario: str,
        choices: dict[str, str],
        foil: str,
        count: int,
        avoid: list[str] | None = None,
    ) -> list[ProposedEdit]:
        _ = original_scenario
        _ = choices
        _ = foil
        _ = count
        self.infill_calls.append(masked_scenario)
        self.avoid_history.append(avoid)
        if self.rounds is None:
            return [
                ProposedEdit(
                    modified_scenario=masked_scenario.replace("[MASK]", "early evening"),
                    rationale="fill highest-ranked span",
                )
            ]
        index = len(self.infill_calls) - 1
        return self.rounds[index] if index < len(self.rounds) else []


def test_s4_occlusion_ranks_top_token_and_masks_it_for_infill() -> None:
    scenario = "Regina is texting in the middle of the night about feeling lonely."
    target = ImportanceTarget()
    proposer = FakeInfillProposer()

    result = S4ImportanceInfillingStrategy(
        candidates_per_round=2,
        max_importance_candidates=6,
    ).generate(
        scenario=scenario,
        choices=CHOICES,
        model=target,
        foil="C",
        budget=10,
        proposer=proposer,
    )

    assert result.status == "success"
    assert result.new_answer == "C"
    assert any("middle of the about" in call for call in target.calls)
    assert proposer.infill_calls[0] == (
        "Regina is texting in the middle of the [MASK] about feeling lonely."
    )
    assert result.attempts[0].edit_description is not None
    assert "mask_count=1" in result.attempts[0].edit_description
    assert "masked_spans='night'" in result.attempts[0].edit_description
    assert "importance_score=" in result.attempts[0].edit_description


def test_s4_falls_back_to_answer_change_scoring_without_logprobs() -> None:
    scenario = "Regina is texting in the middle of the night about feeling lonely."
    target = ImportanceTarget(use_logprobs=False)
    proposer = FakeInfillProposer()

    result = S4ImportanceInfillingStrategy(
        candidates_per_round=2,
        max_importance_candidates=6,
    ).generate(
        scenario=scenario,
        choices=CHOICES,
        model=target,
        foil="C",
        budget=10,
        proposer=proposer,
    )

    assert result.status == "success"
    assert proposer.infill_calls[0].endswith("middle of the [MASK] about feeling lonely.")


def test_s4_increases_mask_proportion_until_smallest_successful_flip() -> None:
    scenario = "Regina feels lonely at night."
    target = TwoSpanTarget()
    proposer = FakeInfillProposer(
        rounds=[
            [
                ProposedEdit(
                    modified_scenario="Regina feels calm at night.",
                    rationale="single span failed",
                )
            ],
            [
                ProposedEdit(
                    modified_scenario="Regina feels calm early evening.",
                    rationale="combined span succeeds",
                )
            ],
        ]
    )

    result = S4ImportanceInfillingStrategy(
        candidates_per_round=1,
        max_importance_candidates=4,
    ).generate(
        scenario=scenario,
        choices=CHOICES,
        model=target,
        foil="C",
        budget=10,
        proposer=proposer,
    )

    assert result.status == "success"
    assert len(result.attempts) == 2
    assert proposer.infill_calls == [
        "Regina feels [MASK] at night.",
        "Regina feels [MASK].",
    ]
    assert result.attempts[0].edit_description is not None
    assert "mask_count=1" in result.attempts[0].edit_description
    assert result.attempts[1].edit_description is not None
    assert "mask_count=2" in result.attempts[1].edit_description


def test_s4_budget_exhaustion_returns_not_found() -> None:
    scenario = "Regina is texting in the middle of the night."
    target = NonFlippingTarget()
    proposer = FakeInfillProposer(
        rounds=[
            [
                ProposedEdit(
                    modified_scenario="Alex is texting in the middle of the night."
                )
            ]
        ]
    )

    result = S4ImportanceInfillingStrategy(
        candidates_per_round=1,
        max_importance_candidates=1,
    ).generate(
        scenario=scenario,
        choices=CHOICES,
        model=target,
        foil="C",
        budget=3,
        proposer=proposer,
    )

    assert result.status == "not_found"
    assert result.new_answer is None
    assert len(target.calls) == 3
    assert len(result.attempts) == 1


def test_s4_rejects_leaks_duplicates_and_outside_mask_edits() -> None:
    scenario = "Regina is texting in the middle of the night."
    valid_nonflip = "Regina is texting in the middle of the early morning."
    outside_mask = "Rachel is texting in the middle of the early evening."
    foil_leak = f"Regina is texting in the middle of the {CHOICES['C']}."
    target = NonFlippingTarget()
    proposer = FakeInfillProposer(
        rounds=[
            [
                ProposedEdit(modified_scenario=valid_nonflip),
                ProposedEdit(modified_scenario=valid_nonflip),
                ProposedEdit(modified_scenario=outside_mask),
                ProposedEdit(modified_scenario=foil_leak),
            ]
        ]
    )

    result = S4ImportanceInfillingStrategy(
        candidates_per_round=4,
        max_importance_candidates=4,
    ).generate(
        scenario=scenario,
        choices=CHOICES,
        model=target,
        foil="C",
        budget=10,
        proposer=proposer,
    )

    assert result.status == "not_found"
    assert len(result.attempts) == 1
    assert result.attempts[0].modified_scenario == valid_nonflip
    assert target.calls.count(valid_nonflip) == 1
    assert outside_mask not in target.calls
    assert foil_leak not in target.calls
