import type { ReactNode } from "react";

import type { ComparisonRow, DiffSpan, StrategyInfo } from "../types/api";

interface SelectedScenarioComparisonTableProps {
  groundTruth: string | null;
  rows: ComparisonRow[];
  strategies: StrategyInfo[];
}

function strategyName(strategyId: string, strategies: StrategyInfo[]) {
  return strategies.find((strategy) => strategy.id === strategyId)?.name ?? strategyId;
}

function statusLabel(status: ComparisonRow["status"]) {
  if (status === "not_found") {
    return "No result";
  }
  if (status === "skipped") {
    return "Skipped";
  }
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function formatPercent(value: number | null) {
  return value === null ? "N/A" : `${(value * 100).toFixed(1)}%`;
}

function formatRuntime(value: number) {
  return value < 0.01 ? "<0.01s" : `${value.toFixed(2)}s`;
}

function resultAnswerLabel(row: ComparisonRow) {
  if (row.new_answer) {
    return row.new_answer;
  }
  if (row.status === "not_found") {
    return "no result";
  }
  if (row.status === "skipped") {
    return "skipped";
  }
  if (row.status === "failed") {
    return "failed";
  }
  return "N/A";
}

function renderHighlightedText(
  text: string,
  diff: DiffSpan[],
  side: "original" | "modified",
) {
  const parts: ReactNode[] = [];
  let cursor = 0;
  let highlighted = false;

  for (const span of diff) {
    const target = side === "original" ? span.original : span.modified;
    if (!target) {
      continue;
    }

    const index = text.indexOf(target, cursor);
    if (index === -1) {
      continue;
    }

    if (index > cursor) {
      parts.push(text.slice(cursor, index));
    }

    parts.push(
      <mark className={side === "original" ? "delete-mark" : "insert-mark"} key={`${side}-${index}`}>
        {target}
      </mark>,
    );
    cursor = index + target.length;
    highlighted = true;
  }

  if (!highlighted) {
    return text;
  }

  if (cursor < text.length) {
    parts.push(text.slice(cursor));
  }

  return <>{parts}</>;
}

function scenarioText(row: ComparisonRow) {
  return row.result?.original_scenario ?? row.question_id;
}

function modifiedScenarioText(row: ComparisonRow) {
  return row.modified_scenario?.trim() || "No scenario generated.";
}

export function SelectedScenarioComparisonTable({
  groundTruth,
  rows,
  strategies,
}: SelectedScenarioComparisonTableProps) {
  if (rows.length === 0) {
    return (
      <div className="status-strip">
        <strong>No selected-scenario rows</strong>
        <span>Run comparison after selecting a scenario in Experiment.</span>
      </div>
    );
  }

  const groupedRows = rows.reduce<Record<string, ComparisonRow[]>>((groups, row) => {
    const foil = row.foil ?? "-";
    return { ...groups, [foil]: [...(groups[foil] ?? []), row] };
  }, {});

  return (
    <div className="selected-comparison-table" aria-label="Selected scenario comparison">
      <div className="selected-comparison-row header" role="row">
        <span>Strategy</span>
        <span>Status</span>
        <span>Answer</span>
        <span>Edit</span>
        <span>Changed</span>
        <span>Target Calls</span>
        <span>Proposer Calls</span>
        <span>Runtime</span>
        <span>View</span>
      </div>
      {Object.entries(groupedRows).map(([foil, foilRows]) => (
        <section className="foil-result-group" key={foil}>
          <div className="foil-result-heading">
            <h3>Foil {foil}</h3>
          </div>
          {foilRows.map((row) => (
            <details className="selected-comparison-details" key={`${row.foil}-${row.strategy_id}`}>
              <summary className="selected-comparison-row">
                <span data-label="Strategy">{strategyName(row.strategy_id, strategies)}</span>
                <span data-label="Status">{statusLabel(row.status)}</span>
                <span data-label="Answer">
                  {row.original_answer ?? "-"} {"->"} {resultAnswerLabel(row)}
                </span>
                <span data-label="Edit">{row.token_edit_distance ?? "N/A"}</span>
                <span data-label="Changed">{formatPercent(row.changed_word_fraction)}</span>
                <span data-label="Target">{row.total_target_calls}</span>
                <span data-label="Proposer">{row.proposer_calls}</span>
                <span data-label="Runtime">{formatRuntime(row.runtime_seconds)}</span>
                <span className="row-details-action" data-label="View">View</span>
              </summary>

              <div className="selected-row-detail">
                <div className="strategy-detail-grid compact">
                  <div>
                    <span className="readout-label">Foil</span>
                    <p>
                      {row.foil ?? "-"}
                      {row.foil === groundTruth ? " (ground truth)" : ""}
                    </p>
                  </div>
                  <div>
                    <span className="readout-label">Status Meaning</span>
                    <p>
                      {row.status === "not_found"
                        ? "No counterfactual found within the budget."
                        : statusLabel(row.status)}
                    </p>
                  </div>
                  <div>
                    <span className="readout-label">Target Calls</span>
                    <p>{row.total_target_calls}</p>
                  </div>
                  <div>
                    <span className="readout-label">Runtime</span>
                    <p>{formatRuntime(row.runtime_seconds)}</p>
                  </div>
                </div>

                <div className="comparison-text-block">
                  <span className="readout-label">Original Scenario</span>
                  <p>{renderHighlightedText(scenarioText(row), row.result?.diff ?? [], "original")}</p>
                </div>

                <div className="comparison-text-block">
                  <span className="readout-label">Modified Scenario</span>
                  <p>{renderHighlightedText(modifiedScenarioText(row), row.result?.diff ?? [], "modified")}</p>
                </div>

                {row.message ? (
                  <div className="insight-box">
                    <p>{row.message}</p>
                  </div>
                ) : null}
              </div>
            </details>
          ))}
        </section>
      ))}
    </div>
  );
}
