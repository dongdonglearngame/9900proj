# Architecture

The project is organized around a fixed contract:

```text
React UI
-> FastAPI routes
-> services
-> repositories / harness / strategy registry
-> local Ollama or mock LLM client
```

Important invariants:

- The target model never sees the foil.
- Target calls are stateless.
- Flip success is `prediction.answer == foil`.
- Logprobs are search signals only.
- `not_found` is a valid result.
- Strategies must call the shared harness, not the LLM client directly.
- Shared post-processing and metrics stay outside individual strategies.

Current state (scaffold):

- The structure, schemas/API contract, strategy interface (`strategies/base.py`) and
  shared metrics/diff utilities are in place; the app runs end-to-end in mock mode.
- Repositories are in-memory for now. The SQLite tables are already defined in
  `db/models.py` (`scenario_items`, `questions`, `predictions`, `counterfactual_jobs`,
  `counterfactuals`, `metrics`) and `db/session.py` / `db/init_db.py` / `db/hashing.py`
  provide the engine, schema bootstrap and cache-key helpers — wiring them in is a TODO.
- The frozen harness, S1, real counterfactual orchestration, EmoBench loader and
  baseline accuracy are `TODO(P18-...)` stubs. See `sprint1-implementation-notes.md`.

Mock mode (`USE_MOCK_LLM=true`) needs no Ollama and no database: `MockLLMClient` serves
predictions, `GET /scenarios` returns built-in mock scenarios, and the counterfactual
endpoint returns a labelled mock placeholder.
