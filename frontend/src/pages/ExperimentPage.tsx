import { useEffect, useState } from "react";

import { getHealth } from "../api/client";
import { ExplanationView } from "../components/ExplanationView";
import { FoilSelector } from "../components/FoilSelector";
import { LoadingStatus } from "../components/LoadingStatus";
import { MetricsPanel } from "../components/MetricsPanel";
import { PredictionView } from "../components/PredictionView";
import { ScenarioInputPanel } from "../components/ScenarioInputPanel";
import { TaskModelSelector } from "../components/TaskModelSelector";

// Shell only. TODO(P18-UI-1 / P18-UI-2): implement the experiment workflow:
//   load models/scenarios/strategies -> select scenario -> predict -> choose foil ->
//   select strategy -> generate counterfactual -> poll job -> show diff + metrics.
// The API client (src/api/client.ts) and response types (src/types/api.ts) are ready.
export function ExperimentPage() {
  const [health, setHealth] = useState<string>("checking");

  useEffect(() => {
    getHealth()
      .then((response) => setHealth(response.status))
      .catch(() => setHealth("offline"));
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">P18 counterfactual explanation</p>
          <h1>Experiment Workspace</h1>
        </div>
        <span className={`health ${health === "ok" ? "ok" : "warn"}`}>{health}</span>
      </header>

      <div className="error-banner">
        Scaffold only - the experiment workflow is not implemented yet (P18-UI-1 / P18-UI-2).
      </div>

      <section className="workspace-grid">
        <div className="left-column">
          <TaskModelSelector />
          <ScenarioInputPanel />
          <div className="action-row">
            <button className="primary-button" disabled>
              Predict
            </button>
            <button className="secondary-button" disabled>
              Generate Counterfactual
            </button>
          </div>
        </div>

        <div className="right-column">
          <PredictionView />
          <FoilSelector />
          <LoadingStatus />
          <ExplanationView />
          <MetricsPanel />
        </div>
      </section>
    </main>
  );
}
