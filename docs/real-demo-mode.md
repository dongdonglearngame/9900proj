# Real Demo Mode

This repository stays mock-safe by default. Real demo mode is a local opt-in setup for
teammates who have Ollama installed and have downloaded EmoBench locally.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Ollama installed locally
- `llama3.2:3b` pulled into Ollama
- EmoBench JSONL files downloaded into `data/raw/`

Official dataset source:

- ACL paper: `https://aclanthology.org/2024.acl-long.326/`
- Code/data repo: `https://github.com/Sahandfer/EmoBench`

Expected local files:

- `data/raw/EU.jsonl`
- `data/raw/EA.jsonl`

These files are gitignored and should stay local.

## 1. Configure the backend

From `backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set:

```text
USE_MOCK_LLM=false
DEFAULT_MODEL=llama3.2:3b
TARGET_PROMPT_VERSION=target-v2-chat-dynamic-choices
```

## 2. Start Ollama

Make sure the Ollama server is running, then pull the model once:

```powershell
ollama serve
ollama pull llama3.2:3b
```

If `ollama serve` is already running in the background, only the `pull` step is needed.

## 3. Import EmoBench into SQLite

From `backend/`:

```powershell
python -m app.scripts.load_emobench --input ..\data\raw\EU.jsonl
python -m app.scripts.load_emobench --input ..\data\raw\EA.jsonl
```

This creates or updates `backend/p18_dev.db`.

## 4. Start backend and frontend

Backend:

```powershell
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd ..\frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open:

- Backend docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`

## 5. Real Demo A sample

This is the current stable real sample for `llama3.2:3b + S1 Word-level Greedy`.

- Task type: `EU`
- Model: `llama3.2:3b`
- Strategy: `S1 Word-level Greedy`
- Example ID: `emobench_q_en_102_emotion`

Original scenario:

```text
Sara has always been very superstitious. Yesterday, despite loving her job, She decided to quit as her office shifted to the 13th floor of her building.
```

Successful S1 edit:

```text
always -> often
```

Modified scenario:

```text
Sara has often been very superstitious. Yesterday, despite loving her job, She decided to quit as her office shifted to the 13th floor of her building.
```

Observed stable behaviour in direct Ollama calls:

- original answer: `B`
- counterfactual answer after edit: `C`

## 6. UI walkthrough

1. Open the frontend.
2. Choose task type `EU`.
3. Choose model `llama3.2:3b`.
4. Choose strategy `S1 Word-level Greedy`.
5. Click `Load EmoBench Example`.
6. In `Example ID`, choose `emobench_q_en_102_emotion`.
7. Click `Run Model Prediction`.
8. Confirm the prediction is `B`.
9. Choose foil `C`.
10. Click `Generate Counterfactual`.
11. Confirm the result changes the scenario from `always` to `often` and flips the answer to `C`.

## Notes

- Do not commit `.env`, `.db`, `.sqlite3`, `.venv`, `node_modules`, or `data/raw/*`.
- Keep `.env.example` in mock-safe mode so CI and teammates without Ollama can still run the repo.
- Real demo mode is a local developer workflow, not the tracked repo default.
