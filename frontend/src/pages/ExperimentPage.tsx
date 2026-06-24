import { useEffect, useState } from "react";

import { getHealth } from "../api/client";
import { ExplanationView } from "../components/ExplanationView";
import { FoilSelector } from "../components/FoilSelector";
import { LoadingStatus } from "../components/LoadingStatus";
import { MetricsPanel } from "../components/MetricsPanel";
import { PredictionView } from "../components/PredictionView";
import { ScenarioInputPanel } from "../components/ScenarioInputPanel";
import { TaskModelSelector } from "../components/TaskModelSelector";
import type {
  ChoiceLetter,
  CounterfactualJob,
  CounterfactualResult,
  ModelInfo,
  PredictResponse,
  ScenarioItem,
  StrategyInfo,
} from "../types/api";

const demoModels: ModelInfo[] = [
  { id: "llama-3.1-8b", name: "Llama 3.1 8B", available: true },
  { id: "mistral-7b", name: "Mistral 7B", available: true },
  { id: "qwen-2.5-7b", name: "Qwen 2.5 7B", available: false },
];

const demoStrategies: StrategyInfo[] = [
  { id: "minimal-edit", name: "Minimal Edit", available: true },
  { id: "semantic-search", name: "Semantic Search", available: true },
];

const demoScenario: ScenarioItem = {
  question_id: "emobench-001",
  scenario_item_id: "regina-loneliness",
  task_type: "identify-best-response",
  dimension: "emotional support",
  subject: "Regina",
  scenario:
    "Regina's best friend recently broke up with her longtime partner and is texting Regina in the middle of the night expressing feelings of loneliness.",
  question_text: "What is the best response?",
  choices: {
    A: "Ignore the texts and continue sleeping",
    B: "Respond telling her friend to seek professional help",
    C: "Stay up and lend a listening ear to her friend",
    D: "Suggest her friend find a new partner",
  },
  label: "C",
};

export function ExperimentPage() {
  const [health, setHealth] = useState<string>("checking");
  const [selectedModel, setSelectedModel] = useState(demoModels[0].id);
  const [selectedStrategy, setSelectedStrategy] = useState(demoStrategies[0].id);
  const [selectedTaskType, setSelectedTaskType] = useState(demoScenario.task_type);
  const [scenarioText, setScenarioText] = useState(demoScenario.scenario);
  const [exampleLoaded, setExampleLoaded] = useState(false);
  const [foil, setFoil] = useState<ChoiceLetter>("D");
  const [prediction, setPrediction] = useState<PredictResponse | null>(null);
  const [job, setJob] = useState<CounterfactualJob | null>(null);
  const [result, setResult] = useState<CounterfactualResult | null>(null);

  useEffect(() => {
    getHealth()
      .then((response) => setHealth(response.status))
      .catch(() => setHealth("offline"));
  }, []);

  const modelName = demoModels.find((model) => model.id === selectedModel)?.name ?? selectedModel;
  const currentStep = result ? 4 : prediction ? 3 : exampleLoaded ? 2 : 1;
  const steps = [
    "Configure",
    "Load Example",
    "Run Model",
    "Counterfactual",
  ];

  function getStepClassName(stepNumber: number) {
    if (stepNumber < currentStep) {
      return "completed";
    }

    if (stepNumber === currentStep) {
      return "current";
    }

    return "upcoming";
  }

  function loadExample() {
    setExampleLoaded(true);
    setScenarioText(demoScenario.scenario);
    setPrediction(null);
    setResult(null);
    setJob(null);
    setFoil("D");
  }

  function runPrediction() {
    setPrediction({
      status: "completed",
      answer: "A",
      answer_text: demoScenario.choices.A,
      model: modelName,
      prompt_template_version: "demo-v1",
      cache_hit: false,
      raw_response: "A",
      option_logprobs: { A: -0.15, B: -1.8, C: -2.4, D: -3.2 },
      option_probs: { A: 0.63, B: 0.18, C: 0.13, D: 0.06 },
      runtime_seconds: 1.42,
    });
    setResult(null);
  }

  function generateCounterfactual() {
    setJob({
      job_id: "demo-counterfactual-job",
      status: "completed",
      phase: "done",
      progress: {
        budget: 12,
        search_calls: 4,
        postprocess_calls: 2,
        proposer_calls: 1,
      },
      result: null,
      message: null,
    });
    setResult({
      status: "success",
      strategy_id: selectedStrategy,
      original_answer: prediction?.answer ?? "A",
      foil: "C",
      new_answer: "C",
      original_scenario: scenarioText,
      modified_scenario:
        "Regina's best friend recently broke up with her longtime partner and is texting Regina in the early evening expressing feelings of loneliness.",
      original_prediction: null,
      new_prediction: null,
      diff: [
        {
          type: "replace",
          original: "middle of the night",
          modified: "early evening",
        },
      ],
      metrics: {
        flip_success: true,
        token_edit_distance: 0.12,
        changed_word_fraction: 0.06,
        perplexity: null,
        fluency_score: 0.87,
        search_calls: 4,
        postprocess_calls: 2,
        proposer_calls: 1,
        total_target_calls: 7,
        runtime_seconds: 3.8,
      },
      message:
        "The model flipped from A to C after a small edit changed the timing from 'middle of the night' to 'early evening'. This suggests that the model's original advice depended more on the time of day than on the friend's emotional distress itself.",
    });
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>Experiment</h1>
          <p>Run EmoBench predictions and generate counterfactual explanations step by step.</p>
        </div>
        <span className={`health ${health === "ok" ? "ok" : "warn"}`}>{health}</span>
      </header>

      <nav className="stepper" aria-label="Experiment progress">
        {steps.map((step, index) => {
          const stepNumber = index + 1;

          return (
            <span className={getStepClassName(stepNumber)} data-step={stepNumber} key={step}>
              {step}
            </span>
          );
        })}
      </nav>

      <section className="single-column-workspace">
        <TaskModelSelector
          models={demoModels}
          selectedModel={selectedModel}
          selectedTaskType={selectedTaskType}
          strategies={demoStrategies}
          selectedStrategy={selectedStrategy}
          onLoadExample={loadExample}
          onModelChange={setSelectedModel}
          onStrategyChange={setSelectedStrategy}
          onTaskTypeChange={setSelectedTaskType}
        />

        {exampleLoaded ? (
          <>
            <ScenarioInputPanel
              choices={demoScenario.choices}
              scenario={demoScenario}
              scenarioText={scenarioText}
              onScenarioTextChange={setScenarioText}
            />

            <button className="gradient-button" type="button" onClick={runPrediction}>
              Run Model Prediction
            </button>
          </>
        ) : null}

        {exampleLoaded && prediction ? (
          <>
            <PredictionView choices={demoScenario.choices} groundTruth={demoScenario.label} prediction={prediction} />
            <FoilSelector
              choices={demoScenario.choices}
              foil={foil}
              originalAnswer={prediction.answer}
              onFoilChange={setFoil}
              onGenerate={generateCounterfactual}
            />
          </>
        ) : null}

        <LoadingStatus job={job} />

        {result ? (
          <>
            <ExplanationView modelName={modelName} result={result} />
            <MetricsPanel metrics={result.metrics} />
            <button className="reset-button" type="button" onClick={loadExample}>
              Start New Experiment
            </button>
          </>
        ) : null}
      </section>
    </main>
  );
}
