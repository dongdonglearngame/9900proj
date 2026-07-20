import json

from app.proposer.clients import MockProposerClient, ProposerCompletion
from app.proposer.harness import (
    ProposerHarness,
    parse_proposed_edits,
    parse_proposed_edits_with_diagnostics,
)
from app.proposer.prompts import build_proposer_messages
from app.schemas.proposer import ProposerCallDiagnostics, ProposerDiagnostics

CHOICES = {
    "A": "Ignore the texts and continue sleeping",
    "B": "Tell her friend to seek professional help",
    "C": "Stay up and lend a listening ear",
    "D": "Suggest her friend find a new partner",
}


def test_parse_proposed_edits_accepts_supported_json_shapes() -> None:
    assert [
        edit.modified_scenario
        for edit in parse_proposed_edits(
            '[{"modified_scenario":"one","rationale":"r1"}, "two"]',
            limit=5,
        )
    ] == ["one", "two"]

    fenced = '```json\n{"rewrites":[{"modified_scenario":"three"}]}\n```'
    assert parse_proposed_edits(fenced, limit=5)[0].modified_scenario == "three"

    dirty = 'Here is JSON: {"rewrites":[{"rewrite":"four"}]}'
    assert parse_proposed_edits(dirty, limit=5)[0].modified_scenario == "four"


def test_parse_proposed_edits_drops_invalid_items_and_truncates() -> None:
    raw = json.dumps(
        {
            "rewrites": [
                {"modified_scenario": ""},
                {"modified_scenario": "one"},
                {"scenario": "two"},
                {"not_a_scenario": "bad"},
                3,
                "three",
            ]
        }
    )

    edits = parse_proposed_edits(raw, limit=2)

    assert [edit.modified_scenario for edit in edits] == ["one", "two"]
    assert parse_proposed_edits("not json", limit=5) == []

    diagnostics = parse_proposed_edits_with_diagnostics(raw, limit=2)
    assert diagnostics.raw_candidates == 6
    assert diagnostics.parsed_candidates == 3
    assert len(diagnostics.edits) == 2


def test_parse_proposed_edits_keeps_optional_quality_fields() -> None:
    result = parse_proposed_edits_with_diagnostics(
        json.dumps(
            {
                "rewrites": [
                    {
                        "modified_scenario": "one",
                        "changed_span": "old -> new",
                        "change_type": "outcome",
                    },
                    {"modified_scenario": "two"},
                    {"not_a_scenario": "invalid"},
                ]
            }
        ),
        limit=5,
    )

    assert result.raw_candidates == 3
    assert result.parsed_candidates == 2
    assert result.edits[0].changed_span == "old -> new"
    assert result.edits[0].change_type == "outcome"
    assert result.edits[1].rationale is None


def test_parse_grounded_span_edit_applies_exact_unique_replacement() -> None:
    scenario = "Leah submitted the form, but the committee rejected it."
    result = parse_proposed_edits_with_diagnostics(
        json.dumps(
            {
                "rewrites": [
                    {
                        "original_span": "rejected",
                        "replacement_span": "approved",
                        "change_type": "outcome",
                    }
                ]
            }
        ),
        limit=4,
        source_scenario=scenario,
        require_grounded_spans=True,
    )

    assert result.raw_candidates == 1
    assert result.parsed_candidates == 1
    assert result.invalid_span_candidates == 0
    assert result.edits[0].modified_scenario == scenario.replace(
        "rejected",
        "approved",
    )
    assert result.edits[0].original_span == "rejected"
    assert result.edits[0].replacement_span == "approved"


def test_parse_grounded_span_edit_rejects_missing_ambiguous_and_noop_spans() -> None:
    result = parse_proposed_edits_with_diagnostics(
        json.dumps(
            {
                "rewrites": [
                    {"original_span": "missing", "replacement_span": "new"},
                    {"original_span": "same", "replacement_span": "new"},
                    {"original_span": "unique", "replacement_span": "unique"},
                    {"modified_scenario": "untrusted full rewrite"},
                ]
            }
        ),
        limit=4,
        source_scenario="same same unique",
        require_grounded_spans=True,
    )

    assert result.edits == []
    assert result.raw_candidates == 4
    assert result.parsed_candidates == 0
    assert result.invalid_span_candidates == 3


class CapturingClient:
    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.options: dict | None = None
        self.messages: list[dict[str, str]] | None = None

    def complete(self, messages: list[dict[str, str]], options: dict) -> str:
        self.messages = messages
        self.options = options
        return self.raw


class DiagnosticClient(CapturingClient):
    def complete(
        self,
        messages: list[dict[str, str]],
        options: dict,
    ) -> ProposerCompletion:
        super().complete(messages, options)
        return ProposerCompletion(
            content=self.raw,
            done_reason="length",
            eval_count=512,
        )


def test_proposer_harness_counts_round_trip_even_on_parse_failure() -> None:
    calls = 0
    client = CapturingClient(raw="not json")

    def record_call() -> None:
        nonlocal calls
        calls += 1

    harness = ProposerHarness(
        client=client,
        original_answer="A",
        temperature=0.7,
        seed=0,
        num_predict=512,
        on_call=record_call,
    )

    edits = harness.propose("scenario", CHOICES, "C", count=4)

    assert edits == []
    assert calls == 1
    assert client.options == {"temperature": 0.7, "seed": 0, "num_predict": 512}
    assert "logprobs" not in client.options


def test_proposer_harness_records_output_length_diagnostics() -> None:
    diagnostics = []
    client = DiagnosticClient(
        raw=json.dumps({"rewrites": [{"modified_scenario": "one"}]})
    )
    harness = ProposerHarness(
        client=client,
        original_answer="A",
        temperature=0.7,
        seed=0,
        num_predict=512,
        on_call=lambda: None,
        on_diagnostics=diagnostics.append,
    )

    edits = harness.propose("scenario", CHOICES, "C", count=4)

    assert [edit.modified_scenario for edit in edits] == ["one"]
    assert len(diagnostics) == 1
    assert diagnostics[0].prompt_version == "s2-proposer-v5-coherence-checklist"
    assert diagnostics[0].requested_candidates == 4
    assert diagnostics[0].seed == 0
    assert diagnostics[0].num_predict == 512
    assert diagnostics[0].temperature == 0.7
    assert diagnostics[0].raw_candidates == 1
    assert diagnostics[0].parsed_candidates == 1
    assert diagnostics[0].delivered_candidates == 1
    assert diagnostics[0].done_reason == "length"
    assert diagnostics[0].eval_count == 512
    assert diagnostics[0].response_tokens == 512
    assert client.messages is not None
    system_prompt = client.messages[0]["content"]
    assert "Modify exactly one existing sentence" in system_prompt
    assert "never change more than 6 words" in system_prompt
    assert "Maya submitted her proposal" in system_prompt
    assert "Everything was suddenly fine" in system_prompt
    assert "Maya felt relieved" not in system_prompt
    assert "He raised the trophy" in system_prompt
    assert "The crowd cheered loudly" in system_prompt
    payload = json.loads(client.messages[-1]["content"])
    assert payload["constraints"] == {
        "allow_new_sentences": False,
        "hard_max_changed_words": 6,
        "modify_exactly_one_existing_sentence": True,
        "preferred_max_changed_words": 3,
    }


def test_s2_prompt_variants_change_only_curated_example_count() -> None:
    prompts = {
        variant: build_proposer_messages(
            scenario="A scenario.",
            choices=CHOICES,
            foil="C",
            original_answer="A",
            count=4,
            variant=variant,
        )[0]["content"]
        for variant in ("zero_shot", "one_shot", "few_shot")
    }

    shared_instruction = "Modify exactly one existing sentence"
    assert all(shared_instruction in prompt for prompt in prompts.values())
    assert "Leah submitted the form" not in prompts["zero_shot"]
    assert "Leah submitted the form" in prompts["one_shot"]
    assert "Noah asked his teammate" not in prompts["one_shot"]
    assert "Leah submitted the form" in prompts["few_shot"]
    assert "Noah asked his teammate" in prompts["few_shot"]
    assert "Tariq's neighbour" in prompts["few_shot"]
    assert "felt relieved" not in prompts["few_shot"]
    assert "Everything was suddenly fine" not in prompts["few_shot"]


def test_proposer_harness_records_selected_prompt_variant() -> None:
    diagnostics = []
    harness = ProposerHarness(
        client=CapturingClient(raw='{"rewrites":[]}'),
        original_answer="A",
        temperature=0.7,
        seed=0,
        num_predict=1024,
        s2_prompt_variant="one_shot",
        on_call=lambda: None,
        on_diagnostics=diagnostics.append,
    )

    harness.propose("scenario", CHOICES, "C", count=4)

    assert diagnostics[0].prompt_version == "s2-proposer-v6-one-shot-curated"


def test_span_grounded_prompt_and_harness_use_deterministic_assembly() -> None:
    scenario = "Noah asked his teammate for help, but she ignored his request."
    diagnostics = []
    client = CapturingClient(
        raw=json.dumps(
            {
                "rewrites": [
                    {
                        "original_span": "ignored",
                        "replacement_span": "answered",
                        "change_type": "behaviour",
                    },
                    {
                        "original_span": "not present",
                        "replacement_span": "answered",
                    },
                ]
            }
        )
    )
    harness = ProposerHarness(
        client=client,
        original_answer="A",
        temperature=0.7,
        seed=0,
        num_predict=1024,
        s2_prompt_variant="span_grounded",
        on_call=lambda: None,
        on_diagnostics=diagnostics.append,
    )

    edits = harness.propose(scenario, CHOICES, "C", count=4)

    assert [edit.modified_scenario for edit in edits] == [
        scenario.replace("ignored", "answered")
    ]
    assert diagnostics[0].prompt_version == "s2-proposer-v7-span-grounded-spike"
    assert diagnostics[0].raw_candidates == 2
    assert diagnostics[0].parsed_candidates == 1
    assert diagnostics[0].invalid_span_candidates == 1
    assert client.messages is not None
    assert "Do not return a rewritten scenario" in client.messages[0]["content"]
    payload = json.loads(client.messages[-1]["content"])
    assert payload["constraints"]["output_mode"] == "exact_span_replacement"


def test_proposer_diagnostics_accept_legacy_payload_without_pr2_fields() -> None:
    call = ProposerCallDiagnostics.model_validate(
        {
            "prompt_version": "legacy",
            "requested_candidates": 1,
            "seed": 0,
            "num_predict": 512,
            "temperature": 0.7,
            "raw_candidates": 1,
            "parsed_candidates": 1,
            "delivered_candidates": 1,
            "latency_seconds": 0.1,
        }
    )
    diagnostics = ProposerDiagnostics.model_validate(
        {
            "calls": [call.model_dump()],
            "requested_candidates": 1,
            "raw_candidates": 1,
            "parsed_candidates": 1,
            "delivered_candidates": 1,
            "unique_valid_candidates": 1,
            "target_verified_candidates": 1,
            "guard_rejections": {},
            "raw_requested_yield": 1.0,
            "parsed_raw_yield": 1.0,
            "unique_valid_requested_yield": 1.0,
            "target_verified_parsed_yield": 1.0,
            "target_verified_delivered_yield": 1.0,
        }
    )

    assert call.invalid_span_candidates == 0
    assert diagnostics.semantic_risks == {}


def test_proposer_harness_increments_seed_for_bounded_refill() -> None:
    client = CapturingClient(raw='{"rewrites":[]}')
    harness = ProposerHarness(
        client=client,
        original_answer="A",
        temperature=0.7,
        seed=7,
        num_predict=512,
        on_call=lambda: None,
    )

    harness.propose("scenario", CHOICES, "C", count=1)
    assert client.options is not None
    assert client.options["seed"] == 7
    harness.propose("scenario", CHOICES, "C", count=1)
    assert client.options["seed"] == 8


def test_proposer_harness_infill_builds_constrained_prompt_and_counts() -> None:
    calls = 0
    diagnostics = []
    client = CapturingClient(
        raw=json.dumps(
            {
                "rewrites": [
                    {
                        "modified_scenario": "Regina texted in the early evening.",
                        "rationale": "fill time mask",
                    }
                ]
            }
        )
    )

    def record_call() -> None:
        nonlocal calls
        calls += 1

    harness = ProposerHarness(
        client=client,
        original_answer="A",
        temperature=0.7,
        seed=0,
        num_predict=512,
        on_call=record_call,
        on_diagnostics=diagnostics.append,
    )

    edits = harness.infill(
        original_scenario="Regina texted in the middle of the night.",
        masked_scenario="Regina texted in the [MASK].",
        choices=CHOICES,
        foil="C",
        count=2,
    )

    assert calls == 1
    assert diagnostics[0].prompt_version == "s4-infill-v1"
    assert edits[0].modified_scenario == "Regina texted in the early evening."
    assert client.messages is not None
    assert "Only replace each [MASK] span" in client.messages[0]["content"]
    payload = json.loads(client.messages[-1]["content"])
    assert payload["masked_scenario"] == "Regina texted in the [MASK]."
    assert payload["original_answer"] == "A"


def test_mock_proposer_returns_json_rewrites_that_parser_exercises() -> None:
    scenario = (
        "Regina's best friend recently broke up and is texting Regina in the "
        "middle of the night."
    )
    raw = MockProposerClient().complete(
        [{"role": "user", "content": json.dumps({"scenario": scenario, "count": 2})}],
        options={},
    )

    edits = parse_proposed_edits(raw, limit=2)

    assert edits
    assert "early evening" in edits[0].modified_scenario


def test_mock_proposer_returns_constrained_infill_rewrites() -> None:
    raw = MockProposerClient().complete(
        [
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "masked_scenario": "Regina texted in the [MASK].",
                        "count": 2,
                    }
                ),
            }
        ],
        options={},
    )

    edits = parse_proposed_edits(raw, limit=2)

    assert [edit.modified_scenario for edit in edits] == [
        "Regina texted in the early evening.",
        "Regina texted in the afternoon.",
    ]
