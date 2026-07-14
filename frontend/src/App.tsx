import { useCallback, useState } from "react";

import { ComparisonPage } from "./pages/ComparisonPage";
import { ExperimentPage } from "./pages/ExperimentPage";
import type { ExperimentContext } from "./types/experiment";

type AppPage = "experiment" | "comparison";

const initialExperimentContext: ExperimentContext = {
  selectedTaskType: "EU",
  selectedModel: "",
  selectedStrategy: "",
  scenario: null,
  scenarioText: "",
};

export default function App() {
  const [page, setPage] = useState<AppPage>("experiment");
  const [experimentContext, setExperimentContext] = useState<ExperimentContext>(
    initialExperimentContext,
  );

  const handleExperimentContextChange = useCallback((nextContext: ExperimentContext) => {
    setExperimentContext(nextContext);
  }, []);

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand-block">
          <h1>Explainable LLMs</h1>
          <p>Research Prototype</p>
        </div>
        <nav className="page-nav" aria-label="Primary navigation">
          <button
            className={page === "experiment" ? "active" : ""}
            type="button"
            onClick={() => setPage("experiment")}
          >
            Experiment
          </button>
          <button
            className={page === "comparison" ? "active" : ""}
            type="button"
            onClick={() => setPage("comparison")}
          >
            Comparison
          </button>
        </nav>
      </aside>
      <div className="page-content">
        {page === "experiment" ? (
          <ExperimentPage onContextChange={handleExperimentContextChange} />
        ) : (
          <ComparisonPage experimentContext={experimentContext} />
        )}
      </div>
    </div>
  );
}
