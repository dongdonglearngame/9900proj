# P18 scaffold — status & where to implement

This repo is a **scaffold**: the structure, API contract, interfaces and shared
utilities are in place and the app runs end-to-end in mock mode. Each feature below is
a `TODO(P18-...)` stub to be implemented on its own feature branch + PR.

## Already in place (don't rebuild)

- Project structure, FastAPI app + routes, CORS, health.
- API contract: `app/schemas/*` and the frontend `src/types/api.ts` + `src/api/client.ts`.
- Strategy interface: `app/strategies/base.py` (+ `registry.py`). Add S2–S6 here without
  touching routes/services.
- Shared utilities (used by all strategies): `app/metrics/edit_distance.py`,
  `app/metrics/diff.py`, `app/metrics/scorer.py`.
- SQLite tables defined: `app/db/models.py`; engine + bootstrap + hashing in
  `app/db/session.py`, `app/db/init_db.py`, `app/db/hashing.py` (not wired yet).
- Mock contract: `MockLLMClient`, mock scenarios, and a mock counterfactual result so
  the frontend is demoable without Ollama/data.

## TODO map (feature → file → issue)

| Feature | File(s) | Issue |
|---|---|---|
| Frozen Ollama harness | `app/llm/ollama_client.py` | P18-HARNESS-1 |
| Logprob extraction | `app/harness/logprobs.py` | P18-HARNESS-2 |
| Answer parser | `app/harness/parser.py` | P18-HARNESS-3 |
| S1 word-level greedy | `app/strategies/s1_word_greedy.py` | P18-CF-3 |
| Counterfactual orchestration | `app/services/counterfactual_service.py` (real `run_job` + `CounterfactualRunContext`) | P18-CF-2 |
| SQLite persistence | `app/repositories/*` (tables already in `db/models.py`) | P18-DATA-1 / P18-CF-2 |
| EmoBench loader | `app/scripts/load_emobench.py` | P18-DATA-2 |
| Baseline accuracy | `app/services/evaluation_service.py` | P18-EVAL-1 |
| Dashboard aggregation | `app/api/routes/dashboard.py` | P18-METRICS-1 |
| Frontend workflow | `frontend/src/pages/ExperimentPage.tsx` + `src/components/*` | P18-UI-1 / P18-UI-2 |

## Decisions / notes

- **SQLite is optional per the client** (CSV is acceptable). The tables are defined so
  persistence can be wired when wanted; until then repositories are in-memory.
- **Python 3.11+** required (`app/db/models.py` uses `datetime.UTC`); CI runs 3.11.
- The root `plan.txt` code blocks are corrupted (slashes/dots stripped). Correct forms:

  ```bash
  uvicorn app.main:app --reload --port 8000
  python -m app.scripts.load_emobench --input ../data/raw/emobench.json   # once implemented
  python -m app.scripts.run_baseline --model llama3.2:3b --task_type EU    # once implemented
  # branches: feat/frozen-harness, feat/s1-counterfactual, feat/emobench-loader, ...
  ```

## Workflow

No direct pushes to `main`; one feature branch + PR per GitHub issue; PRs must pass CI
(`ruff check .` + `pytest` for backend, `npm run build` for frontend).
