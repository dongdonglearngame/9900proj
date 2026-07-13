import type { ComparisonStrategySummary, StrategyInfo } from "../types/api";

interface BatchSummaryTableProps {
  summaries: ComparisonStrategySummary[];
  strategies: StrategyInfo[];
}

function strategyName(strategyId: string, strategies: StrategyInfo[]) {
  return strategies.find((strategy) => strategy.id === strategyId)?.name ?? strategyId;
}

function formatNumber(value: number | null, digits = 2) {
  return value === null ? "N/A" : value.toFixed(digits);
}

function formatPercent(value: number | null) {
  return value === null ? "N/A" : `${(value * 100).toFixed(1)}%`;
}

function formatRuntime(value: number | null) {
  if (value === null) {
    return "N/A";
  }
  return value < 0.01 ? "<0.01s" : `${value.toFixed(2)}s`;
}

export function BatchSummaryTable({ summaries, strategies }: BatchSummaryTableProps) {
  if (summaries.length === 0) {
    return null;
  }

  return (
    <div className="batch-summary-table-wrap">
      <table className="batch-summary-table">
        <thead>
          <tr>
            <th>Strategy</th>
            <th>Runs</th>
            <th>Success</th>
            <th>No Result</th>
            <th>Errors</th>
            <th>Skipped</th>
            <th>Flip Rate</th>
            <th>Avg Edit</th>
            <th>Median Edit</th>
            <th>Avg Changed</th>
            <th>Avg Target Calls</th>
            <th>Avg Proposer Calls</th>
            <th>Avg Runtime</th>
          </tr>
        </thead>
        <tbody>
          {summaries.map((summary) => (
            <tr key={summary.strategy_id}>
              <th scope="row">{strategyName(summary.strategy_id, strategies)}</th>
              <td data-label="Runs">{summary.runs}</td>
              <td data-label="Success">
                {summary.success_count} / {summary.runs}
              </td>
              <td data-label="No Result">
                {summary.not_found_count} / {summary.runs}
              </td>
              <td data-label="Errors">{summary.failed_count}</td>
              <td data-label="Skipped">{summary.skipped_count}</td>
              <td data-label="Flip Rate">{formatPercent(summary.flip_rate)}</td>
              <td data-label="Avg Edit">{formatNumber(summary.avg_token_edit_distance)}</td>
              <td data-label="Median Edit">{formatNumber(summary.median_token_edit_distance)}</td>
              <td data-label="Avg Changed">{formatPercent(summary.avg_changed_word_fraction)}</td>
              <td data-label="Avg Target Calls">{formatNumber(summary.avg_total_target_calls)}</td>
              <td data-label="Avg Proposer Calls">{formatNumber(summary.avg_proposer_calls)}</td>
              <td data-label="Avg Runtime">{formatRuntime(summary.avg_runtime_seconds)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="batch-summary-note">
        <span>No Result means no counterfactual was found within the budget.</span>
        <span>Avg edit, median edit, and avg changed use successful runs only.</span>
        <span>Avg fluency / perplexity: not available.</span>
      </div>
    </div>
  );
}
