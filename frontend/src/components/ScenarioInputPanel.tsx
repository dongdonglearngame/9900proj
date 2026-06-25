import { choiceLetters, type ChoiceMap, type ScenarioItem } from "../types/api";

interface ScenarioInputPanelProps {
  scenario: ScenarioItem;
  scenarioText: string;
  choices: ChoiceMap;
  onScenarioTextChange: (scenarioText: string) => void;
}

export function ScenarioInputPanel({
  scenario,
  scenarioText,
  choices,
  onScenarioTextChange,
}: ScenarioInputPanelProps) {
  const letters = choiceLetters(choices);

  return (
    <section className="panel">
      <div className="section-heading split-heading">
        <div>
          <h2>Step 2 - Benchmark Scenario</h2>
          <p>Read-only. Ground truth is hidden until the model runs.</p>
        </div>
        <span className="pill">EmoBench</span>
      </div>

      <div className="scenario-field">
        <label>
          <span>Scenario</span>
          <textarea
            aria-label="Benchmark scenario"
            value={scenarioText}
            onChange={(event) => onScenarioTextChange(event.target.value)}
          />
        </label>
      </div>

      <div className="readout-block">
        <span>Subject</span>
        <p>{scenario.subject ?? "Not provided"}</p>
      </div>

      <div className="readout-block">
        <span>Candidate Choices</span>
        <div className="choices-list">
          {letters.map((letter) => (
            <div className="choice-card" key={letter}>
              <span className="choice-badge">{letter}</span>
              <p>{choices[letter]}</p>
            </div>
          ))}
        </div>
      </div>

      <p className="hint-text">Choices are read-only until a prediction is made.</p>
    </section>
  );
}
