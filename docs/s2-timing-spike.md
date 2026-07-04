# S2 Timing Spike

Date: 2026-07-04

Environment:

- Model: `llama3.2:3b`
- Task type: `EU`
- Strategy parameters: `subset=3`, `budget=2`, `K=2`, `max_rounds=1`
- Proposer options: `temperature=0.7`, `seed=0`, `num_predict=512`

| Scenario | Original | Foil | Status | Proposer calls | Verify calls | Proposer seconds | Avg verify seconds | Original predict seconds | Total S2 seconds |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| `emobench_q_en_100_cause` | B | A | not_found | 1 | 1 | 2.89 | 1.64 | 9.52 | 4.53 |
| `emobench_q_en_100_emotion` | A | D | not_found | 1 | 0 | 3.04 | 0.00 | 1.61 | 3.04 |
| `emobench_q_en_101_cause` | A | B | not_found | 1 | 1 | 2.93 | 1.67 | 1.69 | 4.60 |

Initial Demo B recommendation:

- Use `budget=2`, `K=2`, `max_rounds=1` for live demos unless a prepared
  scenario is known to need a larger budget.
- Expect roughly 3-5 seconds per scenario after the original prediction call on
  this local setup.
- Keep a small subset for synchronous demos; use the batch runner for larger
  comparison studies.
