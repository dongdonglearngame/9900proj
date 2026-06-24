import type { CounterfactualResult } from "../types/api";

interface ExplanationViewProps {
  modelName: string;
  result: CounterfactualResult;
}

function renderHighlightedText(text: string, target: string, className: string) {
  const index = text.indexOf(target);

  if (index === -1) {
    return text;
  }

  return (
    <>
      {text.slice(0, index)}
      <mark className={className}>{target}</mark>
      {text.slice(index + target.length)}
    </>
  );
}

export function ExplanationView({ modelName, result }: ExplanationViewProps) {
  const modifiedScenario = result.modified_scenario ?? "No counterfactual scenario generated.";

  return (
    <section className="panel explanation-panel">
      <div className="section-heading split-heading">
        <div>
          <h2>Step 5 - Counterfactual Explanation</h2>
          <p>
            Minimal scenario edit that flips the model's answer from {result.original_answer} to {result.foil}.
          </p>
        </div>
        <span className="model-pill">{modelName}</span>
      </div>

      <div className="scenario-comparison">
        <article>
          <span className="readout-label">Original Scenario</span>
          <p>{renderHighlightedText(result.original_scenario, "middle of the night", "delete-mark")}</p>
        </article>
        <article className="modified-card">
          <span className="readout-label">Modified Scenario</span>
          <p>{renderHighlightedText(modifiedScenario, "early evening", "insert-mark")}</p>
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
