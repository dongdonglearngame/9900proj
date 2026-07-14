# S2 dev-20 optimization results

Date: 2026-07-14

## Scope

This comparison uses the same fixed IDs in `s2-dev20-question-ids.txt`: the first 20
EU questions misclassified by `llama3.2:3b`, ordered by question ID. The ground-truth
choice is used as the foil, and the target-call budget is 4.

The reported flip rate is conditional on this error subset. It is not an estimate of
the S2 flip rate over all 400 EU questions. The independent holdout evaluation remains
pending until the S6 optimization stage is complete.

## Before and after

| Metric | Initial diagnostic | Optimized S2 |
|---|---:|---:|
| Scenarios resolved | 20/20 | 20/20 |
| Frozen-harness flips | 1 | 4 |
| Not found | 19 | 16 |
| Failed | 0 | 0 |
| Proposer calls | 39 | 31 |
| Requested candidates | 138 | 111 |
| Raw candidates | 37 | 69 |
| Parsed candidates | 37 | 69 |
| Delivered candidates | not recorded | 67 |
| Unique valid candidates | not recorded | 50 |
| Target-verified candidates | 30 | 45 |
| Raw/requested yield | 0.2681 | 0.6216 |
| Parsed/raw yield | 1.0000 | 1.0000 |
| Unique-valid/requested yield | not recorded | 0.4505 |
| Target-verified/parsed yield | not recorded | 0.6522 |
| Target-verified/delivered yield | not recorded | 0.6716 |

The initial 1/20 flip used a direct morphological cue and is not treated as credible
evidence. The final four flips pass the lexical foil guard, but still require normal
human review for semantic coherence before being promoted as demo examples.

## Guard and logprob diagnostics

- Guard rejections: 1 duplicate/empty, 12 changed-fraction, 4 foil-leak.
- Output termination: 29 `stop`, 0 `length`, and 2 responses without a reason.
- Refill seeds: 20 calls used seed 0 and 11 second-round calls used seed 1.
- Logprob coverage: 45/45 verified candidates.
- Positive foil-logprob movement: 20/45 candidates (`0.4444`).
- Mean of per-run mean foil-logprob deltas: `0.3273` over runs with covered attempts.

Missing logprobs are excluded from delta calculations. Coverage is always reported
alongside the direction and magnitude statistics.

## Reproduction

```powershell
python -m app.scripts.batch_run_counterfactuals `
  --task-type EU `
  --question-ids-file ..\docs\evaluation\s2-dev20-question-ids.txt `
  --model llama3.2:3b `
  --strategies s2_llm_propose_verify `
  --budget 4 `
  --foil-mode single `
  --output s2-dev20.json
```
