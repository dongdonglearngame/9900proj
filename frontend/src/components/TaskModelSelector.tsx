import type { ModelInfo, StrategyInfo } from "../types/api";

interface TaskModelSelectorProps {
  models: ModelInfo[];
  selectedModel: string;
  selectedTaskType: string;
  strategies: StrategyInfo[];
  selectedStrategy: string;
  onModelChange: (modelId: string) => void;
  onTaskTypeChange: (taskType: string) => void;
  onStrategyChange: (strategyId: string) => void;
  onLoadExample: () => void;
}

export function TaskModelSelector({
  models,
  selectedModel,
  selectedTaskType,
  strategies,
  selectedStrategy,
  onModelChange,
  onTaskTypeChange,
  onStrategyChange,
  onLoadExample,
}: TaskModelSelectorProps) {
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h2>Step 1 - Configure &amp; Load</h2>
          <p>Select task type and model, then load a benchmark example.</p>
        </div>
      </div>

      <div className="setup-grid">
        <label>
          <span>Task Type</span>
          <select value={selectedTaskType} onChange={(event) => onTaskTypeChange(event.target.value)}>
            <option value="identify-best-response">Identify Best Response</option>
            <option value="emotion-recognition">Emotion Recognition</option>
            <option value="social-support">Social Support</option>
          </select>
        </label>

        <label>
          <span>Local LLM Model</span>
          <select value={selectedModel} onChange={(event) => onModelChange(event.target.value)}>
            {models.map((model) => (
              <option key={model.id} value={model.id} disabled={!model.available}>
                {model.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Counterfactual Strategy</span>
          <select value={selectedStrategy} onChange={(event) => onStrategyChange(event.target.value)}>
            {strategies.map((strategy) => (
              <option key={strategy.id} value={strategy.id} disabled={!strategy.available}>
                {strategy.name}
              </option>
            ))}
          </select>
        </label>

        <button className="ghost-button load-example-button" type="button" onClick={onLoadExample}>
          Load EmoBench Example
        </button>
      </div>
    </section>
  );
}
