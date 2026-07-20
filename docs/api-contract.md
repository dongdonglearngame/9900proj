# API Contract

Base URL: `http://localhost:8000`

## GET `/health`

Returns backend status.

## GET `/models`

Returns locally supported target models. In mock mode, the default model is marked available.

## GET `/scenarios`

Query params: `task_type`, `dimension`, `limit`, `offset`.

Returns question items ready for MCQA prediction.

## POST `/predict`

Request includes `question_id`, `scenario`, `choices`, and `model`.

Response includes parsed answer, answer text, prompt template version, cache status, raw response, `option_logprobs`, `option_probs`, and runtime.

Missing option logprobs are `null`, never `0` or `-inf`.

## GET `/counterfactual/strategies`

Returns available and planned counterfactual strategies.

## POST `/counterfactual`

Creates an async counterfactual job. Mock mode completes the job through FastAPI background tasks.

## GET `/counterfactual/jobs/{job_id}`

Returns `pending`, `running`, `completed`, or `failed` job state with progress counters and a result payload.

The result payload includes nullable `concept_edit` metadata. For a successful
`s6_concept_causal_editing` result it contains `concept_class`, `original_span`,
`replacement_span`, optional source/target values, and rationale. Other
strategies and `not_found` S6 results return `concept_edit: null`.
S6 proposer diagnostics distinguish the main grounded-concept prompt from the
single optional span-repair prompt by `prompt_version`; repair remains bounded to
one proposer call per strategy run.

Proposer-backed results include `proposer_diagnostics` with per-call prompt version,
seed, generation settings and output metadata,
raw/parsed/delivered candidate counts, guard rejection totals, and candidate-yield
ratios. `raw_requested_yield` may exceed 1 when a model over-generates. Parsed counts
include every valid JSON item; delivered counts apply the requested-candidate limit,
so both target-verified/parsed and target-verified/delivered yields remain explicit.
S2 diagnostics keep non-blocking `semantic_risks` separate from `guard_rejections`.
Per-call `invalid_span_candidates` records exact-span grounding failures for the
experimental span proposer without treating them as target-model attempts.

Result metrics include:

- `foil_logprob_delta`: selected successful candidate minus original foil logprob;
  `null` for not-found results or missing scores.
- `mean_foil_logprob_delta` and `max_foil_logprob_delta`: aggregates over verified
  candidates with both scores present.
- `positive_delta_rate`: positive deltas divided by covered candidate predictions.
- `logprob_coverage`: covered candidate predictions divided by all verified candidate
  predictions. Missing scores are excluded from delta calculations, never coerced to 0.

## POST `/comparison`

Creates an async fixed-subset comparison job. The response contains both `job_id` and
the persisted `experiment_run_id`. All strategies use the same model, scenario subset,
budget, prompt version, and foil plan.

## GET `/comparison/jobs/{job_id}`

Returns comparison progress, per-strategy summaries, individual result rows, and
coverage metadata. Success, not-found, failed, and skipped rows remain visible. Flip
rate uses all scheduled rows as its denominator. Rows expose the same foil-logprob
metrics; summaries report their per-run averages.

## GET `/comparison/runs/{experiment_run_id}`

Returns the comparison job associated with an experiment run. Coverage reports both
resolved/requested scenarios and executed/total units; `partial_coverage` is explicit,
and requested question IDs that were not resolved are listed in
`missing_question_ids`.
