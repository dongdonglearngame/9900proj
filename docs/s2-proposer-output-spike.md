# Proposer output-length spike

Date: 2026-07-14

## Purpose

The initial S2 diagnostic requested four rewrites with `num_predict=512`, but the
proposer usually returned one. This spike separates response truncation from prompt
instruction following before changing the strategy defaults.

## Method

- Model: `llama3.2:3b`
- Temperature: `0.7`
- Seed: `0`
- Cases: the first three questions from the fixed EU dev diagnostic sample
- Grid: `K = 1, 2, 4` and `num_predict = 512, 1024, 1536`
- One proposer call per grid cell and case
- Metrics: `done_reason`, `eval_count`, delivered candidates, full-yield cases, latency

This is a parameter-selection spike, not a flip-rate estimate. The cases are drawn
from a conditional sample of target-model errors and do not represent all EmoBench
questions.

## Results

| K | num_predict | Mean delivered | Full-yield cases | Length stops | Mean latency (s) |
|---:|---:|---:|---:|---:|---:|
| 1 | 512 | 1.00 | 3/3 | 0/3 | 5.33 |
| 1 | 1024 | 1.00 | 3/3 | 0/3 | 4.69 |
| 1 | 1536 | 1.00 | 3/3 | 0/3 | 4.65 |
| 2 | 512 | 1.67 | 2/3 | 0/3 | 4.95 |
| 2 | 1024 | 1.33 | 1/3 | 0/3 | 4.33 |
| 2 | 1536 | 1.33 | 1/3 | 0/3 | 4.38 |
| 4 | 512 | 3.00 | 2/3 | 0/3 | 4.86 |
| 4 | 1024 | 4.00 | 3/3 | 0/3 | 6.49 |
| 4 | 1536 | 4.00 | 3/3 | 0/3 | 6.19 |

No response ended with `done_reason=length`. Under-delivery at 512 was therefore not
caused by the token ceiling alone. `K=4, num_predict=1024` was the smallest tested
configuration that delivered all requested rewrites on all three cases. Increasing
the ceiling to 1536 did not improve candidate yield.

## Decision

- S2: `S2_PROPOSER_CANDIDATES_PER_ROUND=4`
- S2: `S2_PROPOSER_NUM_PREDICT=1024`
- S2: `S2_PROPOSER_MAX_ROUNDS=2`
- S6: `S6_PROPOSER_CANDIDATES_PER_ROUND=4`
- S6: `S6_PROPOSER_NUM_PREDICT=512`
- S6: `S6_PROPOSER_MAX_ROUNDS=2`

The strategy owns bounded refill through `max_rounds`. The proposer harness performs
exactly one model call per invocation.

## S6 cross-branch validation

S6 is not part of this change and was not copied into this branch. Its independent
token setting was validated against the S6 feature branch using the same three cases,
model, seed, temperature, and parameter grid.

| K | num_predict | Mean delivered | Full-yield cases | Length stops | Mean latency (s) |
|---:|---:|---:|---:|---:|---:|
| 1 | 512 | 0.67 | 2/3 | 0/3 | 2.65 |
| 1 | 1024 | 1.00 | 3/3 | 0/3 | 2.58 |
| 1 | 1536 | 1.00 | 3/3 | 0/3 | 2.54 |
| 2 | 512 | 1.00 | 0/3 | 0/3 | 2.41 |
| 2 | 1024 | 1.00 | 0/3 | 0/3 | 2.52 |
| 2 | 1536 | 1.00 | 0/3 | 0/3 | 2.54 |
| 4 | 512 | 1.00 | 0/3 | 0/3 | 2.54 |
| 4 | 1024 | 1.00 | 0/3 | 0/3 | 2.50 |
| 4 | 1536 | 1.00 | 0/3 | 0/3 | 2.49 |

S6 returned approximately one compact edit per call regardless of the requested
count or token ceiling, and no response ended because of length. Raising its ceiling
therefore provided no candidate-yield benefit. The 512-token setting remains the
smallest sufficient option; bounded strategy rounds handle under-delivery.
