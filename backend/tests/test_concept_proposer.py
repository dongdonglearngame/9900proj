import json

from app.proposer.clients import MockProposerClient
from app.proposer.concept_parser import parse_concept_edits
from app.proposer.concepts import (
    CONCEPT_CLASSES,
    apply_concept_edit,
    normalise_concept_class,
)
from app.proposer.harness import ProposerHarness
from app.strategies.base import ConceptEdit

CHOICES = {
    "A": "Ignore the texts and continue sleeping",
    "B": "Tell her friend to seek professional help",
    "C": "Stay up and lend a listening ear",
    "D": "Suggest her friend find a new partner",
}


class CapturingClient:
    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.options: dict | None = None
        self.messages: list[dict[str, str]] | None = None

    def complete(self, messages: list[dict[str, str]], options: dict) -> str:
        self.messages = messages
        self.options = options
        return self.raw


def test_concept_class_normalisation_uses_explicit_aliases() -> None:
    assert normalise_concept_class("Emotional Cause") == "emotional_cause"
    assert normalise_concept_class("perspective-taking") == "perspective"
    assert normalise_concept_class("unknown concept") is None


def test_parse_concept_edits_normalises_and_rejects_invalid_items() -> None:
    raw = json.dumps(
        {
            "edits": [
                {
                    "concept_class": "Emotion Intensity",
                    "original_span": "terrified",
                    "replacement_span": "uneasy",
                    "source_value": "high",
                    "target_value": "low",
                },
                {
                    "concept_class": "invented",
                    "original_span": "one",
                    "replacement_span": "two",
                },
                {
                    "concept_class": "time",
                    "original_span": "night",
                    "replacement_span": "NIGHT",
                },
            ]
        }
    )

    edits = parse_concept_edits(raw, limit=5, allowed_concepts=CONCEPT_CLASSES)

    assert len(edits) == 1
    assert edits[0].concept_class == "emotional_intensity"
    assert edits[0].source_value == "high"


def test_apply_concept_edit_uses_original_offsets_and_requires_unique_span() -> None:
    scenario = "Regina received a message in the Middle of the Night."
    edit = ConceptEdit(
        concept_class="time",
        original_span="middle of the night",
        replacement_span="early evening",
    )

    applied = apply_concept_edit(scenario, edit)

    assert applied is not None
    modified, resolved = applied
    assert modified == "Regina received a message in the early evening."
    assert resolved.original_span == "Middle of the Night"

    ambiguous = ConceptEdit("time", "night", "morning")
    assert apply_concept_edit("night followed another night", ambiguous) is None
    no_op = ConceptEdit("time", "Middle of the Night", "middle of the night")
    assert apply_concept_edit(scenario, no_op) is None


def test_concept_harness_counts_failed_parse_and_sends_structured_payload() -> None:
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
    edits = harness.propose_concept_edits(
        "scenario",
        CHOICES,
        "C",
        count=2,
        allowed_concepts=CONCEPT_CLASSES,
        avoid=["time: 'night' -> 'evening'"],
    )

    assert edits == []
    assert calls == 1
    assert client.messages is not None
    payload = json.loads(client.messages[-1]["content"])
    assert payload["mode"] == "concept_edit"
    assert payload["original_answer"] == "A"
    assert payload["avoid"] == ["time: 'night' -> 'evening'"]
    assert payload["allowed_concepts"] == list(CONCEPT_CLASSES)
    assert client.options == {"temperature": 0.7, "seed": 0, "num_predict": 512}


def test_mock_proposer_returns_parseable_single_concept_edit() -> None:
    scenario = "Regina is texting her friend in the middle of the night."
    raw = MockProposerClient().complete(
        [
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "mode": "concept_edit",
                        "scenario": scenario,
                        "count": 2,
                        "allowed_concepts": list(CONCEPT_CLASSES),
                        "avoid": [],
                    }
                ),
            }
        ],
        options={},
    )

    edits = parse_concept_edits(raw, limit=2, allowed_concepts=CONCEPT_CLASSES)

    assert len(edits) == 1
    assert edits[0].concept_class == "time"
    assert edits[0].original_span == "middle of the night"
    assert edits[0].replacement_span == "early evening"
