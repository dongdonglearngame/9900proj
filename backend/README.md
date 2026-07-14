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

## Loader

Import EmoBench JSONL into SQLite:

```powershell
python -m app.scripts.load_emobench --input ..\data\raw\EU.jsonl
python -m app.scripts.load_emobench --input ..\data\raw\EA.jsonl
```
