import { useEffect, useRef, useState } from "react";

import {
  getCounterfactualJob,
  getHealth,
  getModels,
  getScenarios,
  getStrategies,
  postCounterfactual,
  postPredict,
} from "../api/client";
import { ExplanationView } from "../components/ExplanationView";
import { FoilSelector } from "../components/FoilSelector";
import { LoadingStatus } from "../components/LoadingStatus";
import { MetricsPanel } from "../components/MetricsPanel";
import { PredictionView } from "../components/PredictionView";
import { ScenarioInputPanel } from "../components/ScenarioInputPanel";
import { TaskModelSelector } from "../components/TaskModelSelector";
import type {
  ChoiceMap,
  ChoiceLetter,
  CounterfactualJob,
  CounterfactualResult,
  ModelInfo,
  PredictResponse,
  ScenarioItem,
  StrategyInfo,
} from "../types/api";
import { choiceLetters } from "../types/api";

const jobPollIntervalMs = 400;
const maxJobPolls = 25;

type ScrollTarget = "scenario" | "prediction" | "explanation";

function firstAvailableId(items: Array<{ id: string; available: boolean }>) {
  return items.find((item) => item.available)?.id ?? items[0]?.id ?? "";
}

function defaultFoil(
  choices: ChoiceMap,
  originalAnswer: ChoiceLetter | null,
  label: ChoiceLetter | null,
): ChoiceLetter | null {
  const letters = choiceLetters(choices);
  if (label && label !== originalAnswer) {
    return label;
  }
  return letters.find((letter) => letter !== originalAnswer) ?? null;
}

function sleep(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export function ExperimentPage() {
  const scenarioStepRef = useRef<HTMLDivElement>(null);
  const predictionStepRef = useRef<HTMLDivElement>(null);
  const explanationStepRef = useRef<HTMLDivElement>(null);
  const [health, setHealth] = useState<string>("checking");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [loadedScenarios, setLoadedScenarios] = useState<ScenarioItem[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedStrategy, setSelectedStrategy] = useState("");
  const [selectedTaskType, setSelectedTaskType] = useState("EU");
  const [scenario, setScenario] = useState<ScenarioItem | null>(null);
  const [scenarioText, setScenarioText] = useState("");
  const [foil, setFoil] = useState<ChoiceLetter | null>(null);
  const [prediction, setPrediction] = useState<PredictResponse | null>(null);
  const [job, setJob] = useState<CounterfactualJob | null>(null);
  const [result, setResult] = useState<CounterfactualResult | null>(null);
  const [scrollTarget, setScrollTarget] = useState<ScrollTarget | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingScenario, setIsLoadingScenario] = useState(false);
  const [isPredicting, setIsPredicting] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    getHealth()
      .then((response) => setHealth(response.status))
      .catch(() => setHealth("offline"));
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadOptions() {
      try {
        const [loadedModels, loadedStrategies] = await Promise.all([getModels(), getStrategies()]);
        if (cancelled) {
          return;
        }
        setModels(loadedModels);
        setStrategies(loadedStrategies);
        setSelectedModel(firstAvailableId(loadedModels));
        setSelectedStrategy(firstAvailableId(loadedStrategies));
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load backend options.");
        }
      }
    }

    void loadOptions();

    return () => {
      cancelled = true;
    };
  }, []);

  const modelName = models.find((model) => model.id === selectedModel)?.name ?? selectedModel;
  const currentStep = result ? 4 : prediction ? 3 : scenario ? 2 : 1;
  const steps = [
    "Configure",
    "Load Example",
    "Run Model",
    "Counterfactual",
  ];

  useEffect(() => {
    if (!scrollTarget) {
      return;
    }

    const targetMap = {
      scenario: scenarioStepRef,
      prediction: predictionStepRef,
      explanation: explanationStepRef,
    };
    const target = targetMap[scrollTarget].current;

    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      setScrollTarget(null);
    }
  }, [scrollTarget, scenario, prediction, result]);

  function getStepClassName(stepNumber: number) {
    if (stepNumber < currentStep) {
      return "completed";
    }

    if (stepNumber === currentStep) {
      return "current";
    }

    return "upcoming";
  }

  function handleTaskTypeChange(taskType: string) {
    setSelectedTaskType(taskType);
    setLoadedScenarios([]);
    setScenario(null);
    setScenarioText("");
    setFoil(null);
    setPrediction(null);
    setResult(null);
    setJob(null);
    setError(null);
  }

  function handleModelChange(modelId: string) {
    setSelectedModel(modelId);
    setFoil(defaultFoil(scenario?.choices ?? {}, null, scenario?.label ?? null));
    setPrediction(null);
    setResult(null);
    setJob(null);
    setError(null);
  }

  function handleStrategyChange(strategyId: string) {
    setSelectedStrategy(strategyId);
    setResult(null);
    setJob(null);
    setError(null);
  }

  function handleScenarioTextChange(nextScenarioText: string) {
    setScenarioText(nextScenarioText);
    setPrediction(null);
    setResult(null);
    setJob(null);
    setError(null);
  }

  function applyScenario(nextScenario: ScenarioItem) {
    setScenario(nextScenario);
    setScenarioText(nextScenario.scenario);
    setFoil(defaultFoil(nextScenario.choices, null, nextScenario.label));
    setPrediction(null);
    setResult(null);
    setJob(null);
    setError(null);
  }

  function handleScenarioSelect(questionId: string) {
    const nextScenario = loadedScenarios.find((item) => item.question_id === questionId);
    if (!nextScenario) {
      return;
    }

    applyScenario(nextScenario);
  }

  function handleFoilChange(nextFoil: ChoiceLetter) {
    setFoil(nextFoil);
    setResult(null);
    setJob(null);
    setError(null);
  }

  async function loadExample() {
    setIsLoadingScenario(true);
    setError(null);
    setPrediction(null);
    setResult(null);
    setJob(null);

    try {
      const scenarios = await getScenarios(selectedTaskType);
      const nextScenario = scenarios[0];
      if (!nextScenario) {
        throw new Error(`No scenarios returned for task type ${selectedTaskType}.`);
      }

      setLoadedScenarios(scenarios);
      applyScenario(nextScenario);
      setScrollTarget("scenario");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load scenario.");
    } finally {
      setIsLoadingScenario(false);
    }
  }

  async function runPrediction() {
    if (!scenario || !selectedModel) {
      return;
    }

    setIsPredicting(true);
    setError(null);
    setResult(null);
    setJob(null);

    try {
      const response = await postPredict({
        question_id: scenario.question_id,
        scenario: scenarioText,
        choices: scenario.choices,
        model: selectedModel,
      });
      setPrediction(response);
      setFoil(defaultFoil(scenario.choices, response.answer, scenario.label));
      setScrollTarget("prediction");
    } catch (predictError) {
      setError(predictError instanceof Error ? predictError.message : "Prediction failed.");
    } finally {
      setIsPredicting(false);
    }
  }

  async function generateCounterfactual() {
    if (!scenario || !prediction?.answer || !foil || !selectedModel || !selectedStrategy) {
      return;
    }

    setIsGenerating(true);
    setError(null);
    setResult(null);

    try {
      const created = await postCounterfactual({
        question_id: scenario.question_id,
        scenario: scenarioText,
        choices: scenario.choices,
        model: selectedModel,
        original_answer: prediction.answer,
        foil,
        strategy_id: selectedStrategy,
        budget: 20,
      });

      for (let poll = 0; poll < maxJobPolls; poll += 1) {
        const nextJob = await getCounterfactualJob(created.job_id);
        setJob(nextJob);

        if (nextJob.status === "completed" || nextJob.status === "failed") {
          if (nextJob.result) {
            setResult(nextJob.result);
            setScrollTarget("explanation");
          }
          if (nextJob.status === "failed") {
            throw new Error(nextJob.message ?? "Counterfactual job failed.");
          }
          return;
        }

        await sleep(jobPollIntervalMs);
      }

      throw new Error("Counterfactual job did not finish before the polling limit.");
    } catch (counterfactualError) {
      setError(
        counterfactualError instanceof Error
          ? counterfactualError.message
          : "Counterfactual generation failed.",
      );
    } finally {
      setIsGenerating(false);
    }
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
        {error ? (
          <div className="status-strip error-strip" role="alert">
            <strong>Issue</strong>
            <span>{error}</span>
          </div>
        ) : null}

        <TaskModelSelector
          models={models}
          selectedModel={selectedModel}
          selectedTaskType={selectedTaskType}
          strategies={strategies}
          selectedStrategy={selectedStrategy}
          onLoadExample={loadExample}
          onModelChange={handleModelChange}
          onStrategyChange={handleStrategyChange}
          onTaskTypeChange={handleTaskTypeChange}
        />

        {scenario ? (
          <div className="scroll-anchor" ref={scenarioStepRef}>
            <ScenarioInputPanel
              availableScenarios={loadedScenarios}
              choices={scenario.choices}
              scenario={scenario}
              scenarioText={scenarioText}
              onScenarioSelect={handleScenarioSelect}
              onScenarioTextChange={handleScenarioTextChange}
            />

            <button
              className="gradient-button"
              disabled={isPredicting || !selectedModel}
              type="button"
              onClick={runPrediction}
            >
              {isPredicting ? "Running Prediction" : "Run Model Prediction"}
            </button>
          </div>
        ) : null}

        {!scenario && isLoadingScenario ? (
          <div className="status-strip" role="status">
            <strong>loading</strong>
            <span>Fetching scenarios from the backend.</span>
          </div>
        ) : null}

        {scenario && prediction ? (
          <div className="scroll-anchor" ref={predictionStepRef}>
            <PredictionView choices={scenario.choices} groundTruth={scenario.label} prediction={prediction} />
            <FoilSelector
              choices={scenario.choices}
              disabled={isGenerating}
              foil={foil}
              originalAnswer={prediction.answer}
              onFoilChange={handleFoilChange}
              onGenerate={generateCounterfactual}
            />
          </div>
        ) : null}

        <LoadingStatus job={job} />

        {result ? (
          <div className="scroll-anchor" ref={explanationStepRef}>
            <ExplanationView modelName={modelName} result={result} />
            <MetricsPanel metrics={result.metrics} />
            <button className="reset-button" type="button" onClick={loadExample}>
              Start New Experiment
            </button>
          </div>
        ) : null}
      </section>
    </main>
  );
}
