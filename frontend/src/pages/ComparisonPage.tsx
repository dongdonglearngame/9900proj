import { useEffect, useState } from "react";

import { getHealth, getModels, getStrategies } from "../api/client";
import { BatchComparisonPanel } from "../components/BatchComparisonPanel";
import type { ModelInfo, StrategyInfo } from "../types/api";
import type { ExperimentContext } from "../types/experiment";

function firstAvailableId(items: Array<{ id: string; available: boolean }>) {
  return items.find((item) => item.available)?.id ?? items[0]?.id ?? "";
}

interface ComparisonPageProps {
  experimentContext: ExperimentContext;
}

export function ComparisonPage({ experimentContext }: ComparisonPageProps) {
  const [health, setHealth] = useState("checking");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then((response) => setHealth(response.status))
      .catch(() => setHealth("offline"));
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadOptions() {
      try {
        const [loadedModels, loadedStrategies] = await Promise.all([getModels(), getStrategies()]);
        if (cancelled) {
          return;
        }
        setModels(loadedModels);
        setStrategies(loadedStrategies);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load backend options.");
        }
      }
    }

    void loadOptions();

    return () => {
      cancelled = true;
    };
  }, []);

  const selectedTaskType = experimentContext.selectedTaskType || "EU";
  const selectedModel = experimentContext.selectedModel || firstAvailableId(models);
  const selectedStrategy = experimentContext.selectedStrategy || firstAvailableId(strategies);
  const scenario = experimentContext.scenario;
  const scenarioText = scenario ? experimentContext.scenarioText || scenario.scenario : "";

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>Comparison</h1>
          <p>Run controlled strategy comparisons on one selected scenario and a local batch.</p>
        </div>
        <span className={`health ${health === "ok" ? "ok" : "warn"}`}>{health}</span>
      </header>

      <section className="single-column-workspace">
        {error ? (
          <div className="status-strip error-strip" role="alert">
            <strong>Issue</strong>
            <span>{error}</span>
          </div>
        ) : null}

        <BatchComparisonPanel
          scenario={scenario}
          scenarioText={scenarioText}
          selectedModel={selectedModel}
          selectedStrategy={selectedStrategy}
          selectedTaskType={selectedTaskType}
          strategies={strategies}
        />
      </section>
    </main>
  );
}
