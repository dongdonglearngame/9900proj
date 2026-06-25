# Frontend

Vite + React + TypeScript frontend for the P18 experiment workflow.

## Run

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

The app expects the backend at `VITE_API_BASE_URL`, defaulting to `http://localhost:8000`.

For the local real-model demo setup, see `../docs/real-demo-mode.md`.
