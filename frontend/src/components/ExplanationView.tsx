import type { ReactNode } from "react";

import type { CounterfactualResult, DiffSpan } from "../types/api";

interface ExplanationViewProps {
  modelName: string;
  result: CounterfactualResult;
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

function statusCopy(result: CounterfactualResult) {
  if (result.status === "success") {
    return `Candidate scenario edit that changes the model's answer from ${result.original_answer} to ${result.foil}.`;
  }
  if (result.status === "not_found") {
    return "No counterfactual scenario was found within the search budget.";
  }
  return "Counterfactual generation failed.";
}

export function ExplanationView({ modelName, result }: ExplanationViewProps) {
  const modifiedScenario = result.modified_scenario ?? "No counterfactual scenario generated.";

  return (
    <section className="panel explanation-panel">
      <div className="section-heading split-heading">
        <div>
          <h2>Counterfactual Explanation</h2>
          <p>{statusCopy(result)}</p>
        </div>
        <span className="model-pill">{modelName}</span>
      </div>

      <div className="scenario-comparison">
        <article>
          <span className="readout-label">Original Scenario</span>
          <p>{renderHighlightedText(result.original_scenario, result.diff, "original")}</p>
        </article>
        <article className="modified-card">
          <span className="readout-label">Modified Scenario</span>
          <p>{renderHighlightedText(modifiedScenario, result.diff, "modified")}</p>
        </article>
      </div>

      <div className="result-summary">
        <div>
          <span>Original answer</span>
          <strong className="choice-badge">{result.original_answer}</strong>
        </div>
        <div>
          <span>Target foil</span>
          <strong className="choice-badge purple-badge">{result.foil}</strong>
        </div>
        <div>
          <span>New model answer</span>
          <strong className="choice-badge success-badge">{result.new_answer ?? "-"}</strong>
        </div>
      </div>

      {result.message ? (
        <div className="insight-box">
          <p>{result.message}</p>
        </div>
      ) : null}
    </section>
  );
}
