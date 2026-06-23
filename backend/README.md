# Backend

FastAPI backend for the P18 counterfactual explanation tool. This is a **scaffold**:
the structure, interfaces and API contract are in place and runnable in mock mode;
the feature bodies are `TODO(P18-...)` stubs for the team to implement on feature
branches. See `../docs/sprint1-implementation-notes.md` for the TODO map.

## Run
### Windows (PowerShell)
```powershell
python -m venv .venv          # Python 3.11+ (the code uses datetime.UTC)
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```
### Mac
、、、
python3 -m venv .venv          # Python 3.11+
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
、、、

## Test
### Windows (PowerShell)
```
pytest
ruff check .
```
### Mac
、、、
pytest
ruff check .
、、、
## Mock Contract

With `USE_MOCK_LLM=true` (default) the backend needs no Ollama and no database:

- `GET /scenarios` returns built-in mock scenarios (Regina / Omar).
- `POST /predict` is served by `MockLLMClient` (`middle of the night` predicts `A`,
  `early evening` predicts `C`).
- `POST /counterfactual` + `GET /counterfactual/jobs/{id}` return a clearly-labelled
  **mock placeholder** result so the frontend explanation view is demoable.

The real implementations are stubs to be filled in:

- `app/llm/ollama_client.py`, `app/harness/parser.py`, `app/harness/logprobs.py` — frozen Ollama harness (P18-HARNESS-*)
- `app/strategies/s1_word_greedy.py` — S1 baseline (P18-CF-3)
- `app/services/counterfactual_service.py` — real orchestration (P18-CF-2)
- `app/scripts/load_emobench.py` — EmoBench loader (P18-DATA-2)
- `app/services/evaluation_service.py` — baseline accuracy (P18-EVAL-1)
- repositories — SQLite persistence (tables already defined in `app/db/models.py`)
