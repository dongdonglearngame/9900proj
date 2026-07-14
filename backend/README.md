# Backend

FastAPI backend for the P18 counterfactual explanation tool.

Requires Python 3.11+.

## Run

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Test

```powershell
pytest
ruff check .
```

## Modes

`USE_MOCK_LLM=true` is the default repo-safe mode:

- no Ollama required
- no EmoBench download required
- `/scenarios` falls back to built-in mock scenarios when the database is empty
- `/predict` is served by `MockLLMClient`

`REPO_BACKEND=memory` is the default storage mode. Set `REPO_BACKEND=sqlite` when
counterfactual job checkpoints should survive a backend restart.

For the local real-model setup with Ollama + EmoBench import, see
[../docs/real-demo-mode.md](../docs/real-demo-mode.md).

S4 Importance-guided Infilling requires Ollama 0.12.11+ for logprob ranking. Check the
running Ollama instance and selected model before an S4 experiment:

```powershell
python -m app.scripts.check_ollama_logprobs --model llama3.2:3b
```

### Proposer output-length spike

Create a local JSON case containing `scenario`, `choices`, `original_answer`, and
`foil`, then run the bounded S2 parameter grid:

```powershell
python -m app.scripts.run_proposer_spike `
  --input .\spike-case.json `
  --counts 1 2 4 `
  --num-predict-values 512 1024 1536 `
  --output .\proposer-spike.json
```

Each row reports Ollama `done_reason`, `eval_count`, response tokens, raw, parsed, and
delivered candidate counts, yield, and latency. S2 defaults to four candidates with
`S2_PROPOSER_NUM_PREDICT=1024`; the separate S6 settings remain at four compact edits
with `S6_PROPOSER_NUM_PREDICT=512`.

## Loader

Import EmoBench JSONL into SQLite:

```powershell
python -m app.scripts.load_emobench --input ..\data\raw\EU.jsonl
python -m app.scripts.load_emobench --input ..\data\raw\EA.jsonl
```

## Batch comparison

Run a fixed subset through the same model, budget, and strategy list:

```powershell
python -m app.scripts.batch_run_counterfactuals `
  --task_type EU `
  --limit 20 `
  --model llama3.2:3b `
  --strategies s1_word_greedy,s2_llm_propose_verify `
  --budget 20
```

Use `--question-ids q1,q2,...` or `--question-ids-file ids.txt` to rerun an identical
dev or holdout subset instead of selecting by `--limit` and `--offset`. Add
`--output result.json` to keep the full job payload without printing it to the terminal.

The JSON output includes the captured `experiment_run_id`, per-strategy summary,
individual success/not-found/failed/skipped rows, and explicit coverage metadata.
