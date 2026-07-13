import type { ScenarioItem } from "./api";

export interface ExperimentContext {
  selectedTaskType: string;
  selectedModel: string;
  selectedStrategy: string;
  scenario: ScenarioItem | null;
  scenarioText: string;
}
