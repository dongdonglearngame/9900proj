# P18 Explainable LLMs for Mental Health Support

This repository contains the shared project skeleton for COMP9900 Project 18.

The app is a local counterfactual explanation tool for multiple-choice emotional reasoning tasks. A frozen target-model harness predicts an answer, a user chooses a foil answer, and pluggable counterfactual strategies search for minimal scenario edits that flip the target model to the foil.

## Stack

- Runtime: Python 3.11+, Node.js 20+
- Backend: FastAPI, Pydantic, SQLModel, SQLite-ready repositories
- Frontend: Vite, React, TypeScript
- LLM runtime: local Ollama via a frozen harness
- Default mode: mock-safe workflow, no Ollama or EmoBench data required
- Real demo mode: opt-in local setup documented in `docs/real-demo-mode.md`

## Quick Start

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open:

- Backend docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

For a local real-model demo with Ollama + EmoBench, see [docs/real-demo-mode.md](docs/real-demo-mode.md).

## Development Rules

- Keep `main` runnable.
- Work in feature branches.
- Keep routes thin; put behavior in services.
- Strategies must use the frozen `target_predict` function and must not call the target model directly.
- The target-model prompt must never include the foil.
- `not_found` is a valid counterfactual result, not an exception.

## Suggested Branches

- `feat/project-skeleton`
- `feat/mock-api-contract`
- `feat/emobench-loader`
- `feat/ollama-harness`
- `feat/s1-strategy`
- `feat/experiment-page`
- `feat/async-jobs`
- `feat/metrics-dashboard`
