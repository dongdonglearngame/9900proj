import json

from app.proposer.clients import MockProposerClient
from app.proposer.harness import ProposerHarness, parse_proposed_edits

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


class CapturingClient:
    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.options: dict | None = None
        self.messages: list[dict[str, str]] | None = None

    def complete(self, messages: list[dict[str, str]], options: dict) -> str:
        self.messages = messages
        self.options = options
        return self.raw


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


def test_proposer_harness_infill_builds_constrained_prompt_and_counts() -> None:
    calls = 0
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
    )

    edits = harness.infill(
        original_scenario="Regina texted in the middle of the night.",
        masked_scenario="Regina texted in the [MASK].",
        choices=CHOICES,
        foil="C",
        count=2,
    )

    assert calls == 1
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
