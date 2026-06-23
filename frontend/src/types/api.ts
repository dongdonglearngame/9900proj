export type ChoiceLetter = "A" | "B" | "C" | "D";
export type ChoiceMap = Record<ChoiceLetter, string>;
export type OptionScoreMap = Record<ChoiceLetter, number | null>;

export interface ModelInfo {
  id: string;
  name: string;
  available: boolean;
}

export interface StrategyInfo {
  id: string;
  name: string;
  available: boolean;
}

export interface ScenarioItem {
  question_id: string;
  scenario_item_id: string;
  task_type: string;
  dimension: string;
  subject: string | null;
  scenario: string;
  question_text: string | null;
  choices: ChoiceMap;
  label: ChoiceLetter | null;
}

export interface PredictRequest {
  question_id: string | null;
  scenario: string;
  choices: ChoiceMap;
  model: string;
}

export interface PredictResponse {
  status: string;
  answer: ChoiceLetter | null;
  answer_text: string | null;
  model: string;
  prompt_template_version: string;
  cache_hit: boolean;
  raw_response: string;
  option_logprobs: OptionScoreMap;
  option_probs: OptionScoreMap;
  runtime_seconds: number;
}

export interface CounterfactualCreateRequest {
  question_id: string | null;
  scenario: string;
  choices: ChoiceMap;
  model: string;
  original_answer: ChoiceLetter;
  foil: ChoiceLetter;
  strategy_id: string;
  budget: number;
}

export interface CounterfactualCreateResponse {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
}

export interface CounterfactualProgress {
  budget: number;
  search_calls: number;
  postprocess_calls: number;
  proposer_calls: number;
}

export interface PredictionSnapshot {
  answer: ChoiceLetter | null;
  option_logprobs: OptionScoreMap;
}

export interface DiffSpan {
  type: "insert" | "delete" | "replace";
  original: string;
  modified: string;
}

export interface CounterfactualMetrics {
  flip_success: boolean;
  token_edit_distance: number | null;
  changed_word_fraction: number | null;
  perplexity: number | null;
  fluency_score: number | null;
  search_calls: number;
  postprocess_calls: number;
  proposer_calls: number;
  total_target_calls: number;
  runtime_seconds: number;
}

export interface CounterfactualResult {
  status: "success" | "not_found" | "failed";
  strategy_id: string;
  original_answer: ChoiceLetter;
  foil: ChoiceLetter;
  new_answer: ChoiceLetter | null;
  original_scenario: string;
  modified_scenario: string | null;
  original_prediction: PredictionSnapshot | null;
  new_prediction: PredictionSnapshot | null;
  diff: DiffSpan[];
  metrics: CounterfactualMetrics;
  message: string | null;
}

export interface CounterfactualJob {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  phase: "queued" | "search" | "postprocess" | "metrics" | "done" | "failed";
  progress: CounterfactualProgress;
  result: CounterfactualResult | null;
  message: string | null;
}
