import { choiceLetters, type ChoiceMap, type ScenarioItem } from "../types/api";

interface ScenarioInputPanelProps {
  availableScenarios: ScenarioItem[];
  scenario: ScenarioItem;
  scenarioText: string;
  choices: ChoiceMap;
  onScenarioSelect: (questionId: string) => void;
  onScenarioTextChange: (scenarioText: string) => void;
}

function formatScenarioOption(scenario: ScenarioItem) {
  const subject = scenario.subject?.trim() || "Unknown subject";
  return `${scenario.question_id} | ${scenario.dimension} | ${subject}`;
}

export function ScenarioInputPanel({
  availableScenarios,
  scenario,
  scenarioText,
  choices,
  onScenarioSelect,
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

      {availableScenarios.length > 1 ? (
        <div className="scenario-picker-grid">
          <label>
            <span>Example ID</span>
            <select
              aria-label="Loaded EmoBench example"
              value={scenario.question_id}
              onChange={(event) => onScenarioSelect(event.target.value)}
            >
              {availableScenarios.map((item) => (
                <option key={item.question_id} value={item.question_id}>
                  {formatScenarioOption(item)}
                </option>
              ))}
            </select>
          </label>
        </div>
      ) : null}

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
        <span>Question ID</span>
        <p>{scenario.question_id}</p>
      </div>

      <div className="readout-block">
        <span>Dimension</span>
        <p>{scenario.dimension}</p>
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

      <p className="hint-text">
        Load fetches a batch of EmoBench questions for the selected task type. Switching the
        example clears old predictions and results.
      </p>
    </section>
  );
}
