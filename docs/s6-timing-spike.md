# S6 Timing Spike

This spike checks the real Ollama path before using S6 in a larger comparison run.
It is a small engineering measurement, not an evaluation result.

## Configuration

- Date: 2026-07-14
- Model: `llama3.2:3b`
- Strategy: `s6_concept_causal_editing`
- Target-call budget: 4 per scenario
- Backend mode: real Ollama (`USE_MOCK_LLM=false`)
- Dataset: EmoBench EU scenarios loaded into SQLite

## Results

| Scenario | Original | Foil | Status | Target calls | Proposer calls | Runtime |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `emobench_q_en_100_cause` | B | A | `not_found` | 1 | 2 | 7.041 s |
| `emobench_q_en_100_emotion` | A | D | `not_found` | 1 | 2 | 7.036 s |
| `emobench_q_en_101_cause` | A | B | `not_found` | 1 | 2 | 8.043 s |

Mean end-to-end runtime was 7.37 seconds per scenario. All three jobs completed
normally. The proposer returned parseable structured edits and one candidate per
scenario reached the frozen target model. None of those candidates flipped the
target answer, so the observed flip rate was 0/3.

## Interpretation

`not_found` is a valid bounded-search outcome. This sample confirms that the real
proposer, deterministic span replacement, frozen target verification, accounting,
and asynchronous job path execute end to end. It does not establish S6 quality or
latency for the full dataset. A larger fixed-subset run should report parsing and
guard rejection counts alongside flip rate, because those guard-level counters are
not exposed by the current API payload.
