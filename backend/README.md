# Backend

FastAPI backend for the P18 counterfactual explanation tool.

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

For the local real-model setup with Ollama + EmoBench import, see
[../docs/real-demo-mode.md](../docs/real-demo-mode.md).

## Loader

Import EmoBench JSONL into SQLite:

```powershell
python -m app.scripts.load_emobench --input ..\data\raw\EU.jsonl
python -m app.scripts.load_emobench --input ..\data\raw\EA.jsonl
```
