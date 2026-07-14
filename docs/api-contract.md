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

## POST `/comparison`

Creates an async fixed-subset comparison job. The response contains both `job_id` and
the persisted `experiment_run_id`. All strategies use the same model, scenario subset,
budget, prompt version, and foil plan.

## GET `/comparison/jobs/{job_id}`

Returns comparison progress, per-strategy summaries, individual result rows, and
coverage metadata. Success, not-found, failed, and skipped rows remain visible. Flip
rate uses all scheduled rows as its denominator.

## GET `/comparison/runs/{experiment_run_id}`

Returns the comparison job associated with an experiment run. Coverage reports both
resolved/requested scenarios and executed/total units; `partial_coverage` is explicit,
and requested question IDs that were not resolved are listed in
`missing_question_ids`.
