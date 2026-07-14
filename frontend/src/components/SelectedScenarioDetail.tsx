import { choiceLetters, type SelectedScenarioComparison } from "../types/api";

interface SelectedScenarioDetailProps {
  comparison: SelectedScenarioComparison;
}

export function SelectedScenarioDetail({
  comparison,
}: SelectedScenarioDetailProps) {
  const scenario = comparison.scenario;

  return (
    <section className="comparison-info-panel" aria-label="Selected scenario detail">
      <h3>Selected Scenario Detail</h3>
      <div className="selected-scenario-layout">
        <div className="comparison-text-block standalone">
          <span className="readout-label">Scenario Text</span>
          <p>{scenario.scenario}</p>
        </div>
        <dl className="scenario-meta-list">
          <div>
            <dt>Question ID</dt>
            <dd>{scenario.question_id}</dd>
          </div>
        </dl>
      </div>
      <div className="choices-list compact">
        {choiceLetters(scenario.choices).map((letter) => (
          <div className="choice-card" key={letter}>
            <span className="choice-badge">{letter}</span>
            <p>{scenario.choices[letter]}</p>
            <span className="choice-tags">
              {letter === comparison.original_answer ? (
                <span className="choice-tag prediction-tag">Original prediction</span>
              ) : null}
              {letter === comparison.ground_truth ? (
                <span className="choice-tag">Ground truth</span>
              ) : null}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
