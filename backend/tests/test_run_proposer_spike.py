import json

from app.proposer.clients import ProposerCompletion
from app.scripts.run_proposer_spike import run_spike


class FakeClient:
    def complete(self, messages: list[dict[str, str]], options: dict) -> ProposerCompletion:
        requested = json.loads(messages[-1]["content"])["count"]
        rewrites = [
            {"modified_scenario": f"candidate {index}"}
            for index in range(min(requested, 2))
        ]
        return ProposerCompletion(
            content=json.dumps({"rewrites": rewrites}),
            done_reason="stop",
            eval_count=20,
        )


def test_run_spike_records_each_grid_cell_and_output_metadata() -> None:
    report = run_spike(
        client=FakeClient(),
        scenario="scenario",
        choices={"A": "one", "B": "two"},
        original_answer="A",
        foil="B",
        counts=[1, 4],
        num_predict_values=[512, 1024],
        temperature=0.7,
        seed=5,
        repetitions=1,
    )

    assert len(report["rows"]) == 4
    under_delivered = report["rows"][-1]
    assert under_delivered["count"] == 4
    assert under_delivered["num_predict"] == 1024
    assert under_delivered["raw_candidates"] == 2
    assert under_delivered["parsed_candidates"] == 2
    assert under_delivered["delivered_candidates"] == 2
    assert under_delivered["raw_requested_yield"] == 0.5
    assert under_delivered["done_reason"] == "stop"
    assert under_delivered["response_tokens"] == 20
