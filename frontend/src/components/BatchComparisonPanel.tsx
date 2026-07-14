import { useEffect, useMemo, useState } from "react";

import { getComparisonJob, postComparison } from "../api/client";
import type {
  ComparisonJob,
  FoilMode,
  ScenarioItem,
  StrategyInfo,
} from "../types/api";
import { BatchSummaryTable } from "./BatchSummaryTable";
import { SelectedScenarioComparisonTable } from "./SelectedScenarioComparisonTable";
import { SelectedScenarioDetail } from "./SelectedScenarioDetail";

const comparisonPollIntervalMs = 1000;
const maxComparisonPolls = 1800;

interface BatchComparisonPanelProps {
  scenario: ScenarioItem | null;
  scenarioText: string;
  selectedModel: string;
  selectedStrategy: string;
  selectedTaskType: string;
  strategies: StrategyInfo[];
}

type RunScope = "selected" | "batch";

function sleep(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function defaultStrategyIds(strategies: StrategyInfo[], selectedStrategy: string) {
  const available = strategies.filter((strategy) => strategy.available).map((strategy) => strategy.id);
  if (!available.includes(selectedStrategy)) {
    return available;
  }
  return [selectedStrategy, ...available.filter((strategyId) => strategyId !== selectedStrategy)];
}

function strategyNames(strategyIds: string[], strategies: StrategyInfo[]) {
  return strategyIds
    .map((strategyId) => strategies.find((strategy) => strategy.id === strategyId)?.name ?? strategyId)
    .join(", ");
}

function foilModeLabel(foilMode: FoilMode) {
  return foilMode === "all_non_original"
    ? "All non-original foils"
    : "One fixed foil per scenario";
}

function estimatedFoils(foilMode: FoilMode, scenario: ScenarioItem | null) {
  if (foilMode === "single") {
    return 1;
  }
  if (scenario) {
    return Math.max(Object.keys(scenario.choices).length - 1, 1);
  }
  return 3;
}

function estimatedBatchFoils(foilMode: FoilMode) {
  return foilMode === "single" ? 1 : 5;
}

function uniqueQuestionCount(job: ComparisonJob | null) {
  const rows = job?.result?.rows ?? [];
  return new Set(rows.map((row) => row.question_id)).size;
}

function uniqueFoilCaseCount(job: ComparisonJob | null) {
  const rows = job?.result?.rows ?? [];
  return new Set(
    rows
      .filter((row) => row.foil)
      .map((row) => `${row.question_id}:${row.foil}`),
  ).size;
}

function strategyRunCount(job: ComparisonJob | null) {
  return job?.result?.summary.reduce((total, summary) => total + summary.runs, 0) ?? null;
}

function formatProgress(job: ComparisonJob | null) {
  if (!job || job.status === "completed") {
    return null;
  }
  return (
    <div className="status-strip" role="status">
      <strong>{job.status}</strong>
      <span>
        Progress: {job.progress.completed_units} / {job.progress.total_units}
      </span>
      <span>Skipped: {job.progress.skipped_units}</span>
      {job.progress.current_question_id ? <span>{job.progress.current_question_id}</span> : null}
    </div>
  );
}

export function BatchComparisonPanel({
  scenario,
  scenarioText,
  selectedModel,
  selectedStrategy,
  selectedTaskType,
  strategies,
}: BatchComparisonPanelProps) {
  const [selectedBudget, setSelectedBudget] = useState(5);
  const [selectedFoilMode, setSelectedFoilMode] = useState<FoilMode>("all_non_original");
  const [batchLimit, setBatchLimit] = useState(5);
  const [batchBudget, setBatchBudget] = useState(5);
  const [batchFoilMode, setBatchFoilMode] = useState<FoilMode>("all_non_original");
  const [selectedJob, setSelectedJob] = useState<ComparisonJob | null>(null);
  const [batchJob, setBatchJob] = useState<ComparisonJob | null>(null);
  const [selectedError, setSelectedError] = useState<string | null>(null);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [runningScope, setRunningScope] = useState<RunScope | null>(null);

  const defaultIds = useMemo(
    () => defaultStrategyIds(strategies, selectedStrategy),
    [strategies, selectedStrategy],
  );
  const [strategyIds, setStrategyIds] = useState<string[]>([]);

  useEffect(() => {
    const available = new Set(defaultIds);
    setStrategyIds((current) => {
      const valid = current.filter((strategyId) => available.has(strategyId));
      const next = valid.length > 0 ? valid : defaultIds;
      if (
        next.length === current.length
        && next.every((strategyId, index) => strategyId === current[index])
      ) {
        return current;
      }
      return next;
    });
  }, [defaultIds]);

  useEffect(() => {
    setSelectedJob(null);
    setSelectedError(null);
  }, [scenario?.question_id, scenarioText, selectedModel, selectedTaskType]);

  useEffect(() => {
    setBatchJob(null);
    setBatchError(null);
  }, [selectedModel, selectedTaskType]);

  useEffect(() => {
    setSelectedJob(null);
    setBatchJob(null);
    setSelectedError(null);
    setBatchError(null);
  }, [strategyIds]);

  useEffect(() => {
    setSelectedJob(null);
    setSelectedError(null);
  }, [selectedBudget, selectedFoilMode]);

  useEffect(() => {
    setBatchJob(null);
    setBatchError(null);
  }, [batchBudget, batchFoilMode, batchLimit]);

  function toggleStrategy(strategyId: string) {
    setStrategyIds((current) => {
      if (!current.includes(strategyId)) {
        return [...current, strategyId];
      }
      if (current.length === 1) {
        return current;
      }
      return current.filter((candidate) => candidate !== strategyId);
    });
  }

  async function runComparison(scope: RunScope) {
    if (!selectedModel || strategyIds.length === 0) {
      return;
    }

    const isSelectedRun = scope === "selected";
    if (isSelectedRun && !scenario) {
      setSelectedError("Load a scenario in Experiment before running selected-scenario comparison.");
      return;
    }

    const setJob = isSelectedRun ? setSelectedJob : setBatchJob;
    const setError = isSelectedRun ? setSelectedError : setBatchError;
    const budget = isSelectedRun ? selectedBudget : batchBudget;
    const foilMode = isSelectedRun ? selectedFoilMode : batchFoilMode;
    const selectedScenario = isSelectedRun && scenario ? { ...scenario, scenario: scenarioText } : null;

    setRunningScope(scope);
    setError(null);
    setJob(null);

    try {
      const created = await postComparison({
        model: selectedModel,
        strategy_ids: strategyIds,
        selected_scenario: selectedScenario,
        selected_question_id: selectedScenario?.question_id ?? null,
        question_ids: isSelectedRun && selectedScenario ? [selectedScenario.question_id] : null,
        task_type: selectedTaskType,
        dimension: null,
        limit: isSelectedRun ? 1 : batchLimit,
        offset: 0,
        budget,
        foil_mode: foilMode,
      });

      for (let poll = 0; poll < maxComparisonPolls; poll += 1) {
        const nextJob = await getComparisonJob(created.job_id);
        setJob(nextJob);

        if (nextJob.status === "completed") {
          return;
        }
        if (nextJob.status === "failed") {
          throw new Error(nextJob.message ?? "Comparison job failed.");
        }

        await sleep(comparisonPollIntervalMs);
      }

      throw new Error("Comparison job did not finish within the polling window.");
    } catch (comparisonError) {
      setError(
        comparisonError instanceof Error ? comparisonError.message : "Comparison run failed.",
      );
    } finally {
      setRunningScope(null);
    }
  }

  const selectedResult = selectedJob?.result?.selected_scenario ?? null;
  const batchResult = batchJob?.result ?? null;
  const selectedFoilCount = estimatedFoils(selectedFoilMode, scenario);
  const selectedEstimatedRuns = selectedFoilCount * strategyIds.length;
  const batchEstimatedRuns = batchLimit * estimatedBatchFoils(batchFoilMode) * strategyIds.length;
  const batchCompletedRuns = strategyRunCount(batchJob);
  const batchScenarioCount = uniqueQuestionCount(batchJob);
  const batchFoilCaseCount = uniqueFoilCaseCount(batchJob);
  const selectedCoverage = selectedJob?.result?.coverage ?? null;
  const batchCoverage = batchResult?.coverage ?? null;

  return (
    <section className="comparison-page-grid">
      <section className="panel comparison-panel">
        <div className="section-heading">
          <h2>Strategies</h2>
          <p>Fixed strategy set for selected and batch runs.</p>
        </div>
        <div className="comparison-strategy-picker" aria-label="Comparison strategies">
          {strategies.filter((strategy) => strategy.available).map((strategy) => (
            <label className="strategy-toggle" key={strategy.id}>
              <input
                checked={strategyIds.includes(strategy.id)}
                disabled={runningScope !== null}
                type="checkbox"
                onChange={() => toggleStrategy(strategy.id)}
              />
              <span>{strategy.name}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="panel comparison-panel">
        <div className="section-heading">
          <h2>Selected Scenario Comparison</h2>
          <p>Runs only the current scenario inherited from Experiment.</p>
        </div>

        {scenario ? (
          <>
            <div className="comparison-context-strip" aria-label="Selected scenario run context">
              <span>Scenario: {scenario.question_id}</span>
              <span>Task: {selectedTaskType || "EU"}</span>
              <span>Model: {selectedModel || "Loading"}</span>
              <span>Strategies: {strategyIds.length}</span>
              <span>Runs: {selectedEstimatedRuns}</span>
              {selectedJob ? <span>Run: {selectedJob.experiment_run_id}</span> : null}
            </div>

            <div className="comparison-config-grid two-controls">
              <label>
                <span>Target Verification Budget</span>
                <input
                  disabled={runningScope !== null}
                  max={100}
                  min={1}
                  type="number"
                  value={selectedBudget}
                  onChange={(event) => setSelectedBudget(Number(event.target.value))}
                />
              </label>

              <label>
                <span>Foil Mode</span>
                <select
                  disabled={runningScope !== null}
                  value={selectedFoilMode}
                  onChange={(event) => setSelectedFoilMode(event.target.value as FoilMode)}
                >
                  <option value="single">Single fixed foil</option>
                  <option value="all_non_original">All non-original foils</option>
                </select>
              </label>
            </div>

            {!selectedResult ? (
              <div className="comparison-info-panel">
                <h3>Selected Scenario Input</h3>
                <div className="comparison-text-block standalone">
                  <span className="readout-label">Scenario Text</span>
                  <p>{scenarioText}</p>
                </div>
                <div className="comparison-context-strip">
                  <span>Strategies: {strategyNames(strategyIds, strategies)}</span>
                  <span>Foil mode: {foilModeLabel(selectedFoilMode)}</span>
                  <span>Budget: {selectedBudget} target-verification attempts per strategy per foil</span>
                </div>
              </div>
            ) : null}

            <button
              className="gradient-button"
              disabled={runningScope !== null || !selectedModel || strategyIds.length === 0}
              type="button"
              onClick={() => void runComparison("selected")}
            >
              {runningScope === "selected" ? "Running Selected Scenario" : "Run Selected Scenario Comparison"}
            </button>

            {formatProgress(selectedJob)}

            {selectedError ? (
              <div className="status-strip error-strip" role="alert">
                <strong>Issue</strong>
                <span>{selectedError}</span>
              </div>
            ) : null}

            {selectedResult ? (
              <div className="comparison-results">
                {selectedCoverage ? (
                  <div className="status-strip" role="status">
                    <strong>{selectedCoverage.partial_coverage ? "Partial coverage" : "Complete coverage"}</strong>
                    <span>
                      Scenarios: {selectedCoverage.resolved_scenarios} / {selectedCoverage.requested_scenarios}
                    </span>
                    <span>
                      Executed: {selectedCoverage.completed_units} / {selectedCoverage.total_units}
                    </span>
                  </div>
                ) : null}
                <SelectedScenarioDetail comparison={selectedResult} />
                <SelectedScenarioComparisonTable
                  groundTruth={selectedResult.ground_truth}
                  rows={selectedResult.rows}
                  strategies={strategies}
                />
              </div>
            ) : null}
          </>
        ) : (
          <div className="status-strip">
            <strong>No selected scenario</strong>
            <span>Load a scenario in Experiment to enable this section.</span>
          </div>
        )}
      </section>

      <section className="panel comparison-panel">
        <div className="section-heading">
          <h2>Batch Summary Comparison</h2>
          <p>Runs a benchmark subset and reports aggregate strategy metrics.</p>
        </div>

        <div className="comparison-config-grid">
          <label>
            <span>Batch Size</span>
            <select
              disabled={runningScope !== null}
              value={batchLimit}
              onChange={(event) => setBatchLimit(Number(event.target.value))}
            >
              <option value={5}>5 scenarios</option>
              <option value={10}>10 scenarios</option>
              <option value={20}>20 scenarios</option>
              <option value={50}>50 scenarios</option>
              <option value={200}>200 scenarios</option>
            </select>
          </label>

          <label>
            <span>Target Verification Budget</span>
            <input
              disabled={runningScope !== null}
              max={100}
              min={1}
              type="number"
              value={batchBudget}
              onChange={(event) => setBatchBudget(Number(event.target.value))}
            />
          </label>

          <label>
            <span>Foil Mode</span>
            <select
              disabled={runningScope !== null}
              value={batchFoilMode}
              onChange={(event) => setBatchFoilMode(event.target.value as FoilMode)}
            >
              <option value="single">Single fixed foil</option>
              <option value="all_non_original">All non-original foils</option>
            </select>
          </label>
        </div>

        <div className="comparison-context-strip" aria-label="Batch run context">
          <span>Subset: first {batchLimit} scenarios for {selectedTaskType || "EU"}</span>
          <span>Model: {selectedModel || "Loading"}</span>
          <span>Strategies: {strategyIds.length}</span>
          <span>Estimated runs: up to {batchEstimatedRuns}</span>
          {batchCompletedRuns !== null ? <span>Recorded strategy runs: {batchCompletedRuns}</span> : null}
          {batchJob ? <span>Run: {batchJob.experiment_run_id}</span> : null}
        </div>

        <div className="comparison-context-strip">
          <span>Foil mode: {foilModeLabel(batchFoilMode)}</span>
          <span>Budget: {batchBudget} target-verification attempts per strategy per foil</span>
        </div>

        <button
          className="gradient-button"
          disabled={runningScope !== null || !selectedModel || strategyIds.length === 0}
          type="button"
          onClick={() => void runComparison("batch")}
        >
          {runningScope === "batch" ? "Running Batch" : "Run Batch Comparison"}
        </button>

        {formatProgress(batchJob)}

        {batchError ? (
          <div className="status-strip error-strip" role="alert">
            <strong>Issue</strong>
            <span>{batchError}</span>
          </div>
        ) : null}

        {batchResult ? (
          <div className="comparison-results">
            {batchCoverage ? (
              <div className="status-strip" role="status">
                <strong>{batchCoverage.partial_coverage ? "Partial coverage" : "Complete coverage"}</strong>
                <span>
                  Scenarios: {batchCoverage.resolved_scenarios} / {batchCoverage.requested_scenarios}
                </span>
                <span>
                  Executed: {batchCoverage.completed_units} / {batchCoverage.total_units}
                </span>
                {batchCoverage.missing_question_ids.length > 0 ? (
                  <span>Missing IDs: {batchCoverage.missing_question_ids.join(", ")}</span>
                ) : null}
              </div>
            ) : null}
            <div className="section-heading">
              <h2>Batch Summary Results</h2>
              <p>
                {batchScenarioCount} scenarios produced {batchFoilCaseCount} concrete foil cases
                {" "}and {batchCompletedRuns} recorded strategy rows.
              </p>
            </div>
            <BatchSummaryTable summaries={batchResult.summary} strategies={strategies} />
          </div>
        ) : null}
      </section>
    </section>
  );
}
