import type {
  CounterfactualCreateRequest,
  CounterfactualCreateResponse,
  CounterfactualJob,
  ModelInfo,
  PredictRequest,
  PredictResponse,
  ScenarioItem,
  StrategyInfo,
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function getHealth(): Promise<{ status: string }> {
  return request<{ status: string }>("/health");
}

export async function getModels(): Promise<ModelInfo[]> {
  const data = await request<{ models: ModelInfo[] }>("/models");
  return data.models;
}

export async function getStrategies(): Promise<StrategyInfo[]> {
  const data = await request<{ strategies: StrategyInfo[] }>("/counterfactual/strategies");
  return data.strategies;
}

export async function getScenarios(taskType?: string): Promise<ScenarioItem[]> {
  const params = new URLSearchParams({ limit: "50" });
  if (taskType) {
    params.set("task_type", taskType);
  }
  const data = await request<{ items: ScenarioItem[]; total: number }>(
    `/scenarios?${params.toString()}`,
  );
  return data.items;
}

export async function postPredict(payload: PredictRequest): Promise<PredictResponse> {
  return request<PredictResponse>("/predict", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function postCounterfactual(
  payload: CounterfactualCreateRequest,
): Promise<CounterfactualCreateResponse> {
  return request<CounterfactualCreateResponse>("/counterfactual", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCounterfactualJob(jobId: string): Promise<CounterfactualJob> {
  return request<CounterfactualJob>(`/counterfactual/jobs/${jobId}`);
}
