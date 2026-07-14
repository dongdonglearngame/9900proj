export type ChoiceLetter = string;
export type ChoiceMap = Record<string, string>;
export type OptionScoreMap = Record<string, number | null>;

export function choiceLetters(choices: ChoiceMap): ChoiceLetter[] {
  return Object.keys(choices).sort((left, right) => left.localeCompare(right));
}

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
  foil_logprob_delta: number | null;
  mean_foil_logprob_delta: number | null;
  max_foil_logprob_delta: number | null;
  positive_delta_rate: number | null;
  logprob_coverage: number | null;
}

export interface ProposerCallDiagnostics {
  prompt_version: string;
  requested_candidates: number;
  seed: number;
  num_predict: number;
  temperature: number;
  raw_candidates: number;
  parsed_candidates: number;
  delivered_candidates: number;
  done_reason: string | null;
  eval_count: number | null;
  response_tokens: number | null;
  latency_seconds: number;
}

export interface ProposerDiagnostics {
  calls: ProposerCallDiagnostics[];
  requested_candidates: number;
  raw_candidates: number;
  parsed_candidates: number;
  delivered_candidates: number;
  unique_valid_candidates: number;
  target_verified_candidates: number;
  guard_rejections: Record<string, number>;
  raw_requested_yield: number | null;
  parsed_raw_yield: number | null;
  unique_valid_requested_yield: number | null;
  target_verified_parsed_yield: number | null;
  target_verified_delivered_yield: number | null;
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
  proposer_diagnostics: ProposerDiagnostics | null;
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

export type FoilMode = "single" | "all_non_original";

export interface ComparisonCreateRequest {
  model: string;
  strategy_ids: string[];
  selected_scenario?: ScenarioItem | null;
  selected_question_id?: string | null;
  question_ids?: string[] | null;
  task_type: string | null;
  dimension: string | null;
  limit: number;
  offset: number;
  budget: number;
  foil_mode: FoilMode;
}

export interface ComparisonCreateResponse {
  job_id: string;
  experiment_run_id: string;
  status: "pending" | "running" | "completed" | "failed";
}

export interface ComparisonProgress {
  total_units: number;
  completed_units: number;
  skipped_units: number;
  current_question_id: string | null;
  current_strategy_id: string | null;
  current_foil: ChoiceLetter | null;
}

export interface ComparisonRow {
  experiment_run_id: string;
  question_id: string;
  scenario_item_id: string;
  task_type: string;
  dimension: string;
  model: string;
  strategy_id: string;
  original_answer: ChoiceLetter | null;
  foil: ChoiceLetter | null;
  ground_truth: ChoiceLetter | null;
  status: "success" | "not_found" | "failed" | "skipped";
  new_answer: ChoiceLetter | null;
  flip_success: boolean;
  token_edit_distance: number | null;
  changed_word_fraction: number | null;
  search_calls: number;
  postprocess_calls: number;
  proposer_calls: number;
  total_target_calls: number;
  runtime_seconds: number;
  original_logprobs: OptionScoreMap;
  foil_logprob_delta: number | null;
  mean_foil_logprob_delta: number | null;
  max_foil_logprob_delta: number | null;
  positive_delta_rate: number | null;
  logprob_coverage: number | null;
  modified_scenario: string | null;
  message: string | null;
  result: CounterfactualResult | null;
}

export interface ComparisonStrategySummary {
  strategy_id: string;
  runs: number;
  attempted_count: number;
  success_count: number;
  not_found_count: number;
  failed_count: number;
  skipped_count: number;
  flip_rate: number | null;
  coverage_rate: number | null;
  partial_coverage: boolean;
  avg_token_edit_distance: number | null;
  median_token_edit_distance: number | null;
  avg_changed_word_fraction: number | null;
  avg_total_target_calls: number | null;
  avg_proposer_calls: number | null;
  avg_runtime_seconds: number | null;
  avg_foil_logprob_delta: number | null;
  avg_mean_foil_logprob_delta: number | null;
  avg_max_foil_logprob_delta: number | null;
  avg_positive_delta_rate: number | null;
  avg_logprob_coverage: number | null;
}

export interface SelectedScenarioComparison {
  scenario: ScenarioItem;
  original_answer: ChoiceLetter | null;
  ground_truth: ChoiceLetter | null;
  foils: ChoiceLetter[];
  rows: ComparisonRow[];
}

export interface ComparisonCoverage {
  requested_scenarios: number;
  resolved_scenarios: number;
  missing_question_ids: string[];
  total_units: number;
  completed_units: number;
  skipped_units: number;
  scenario_coverage_rate: number | null;
  execution_coverage_rate: number | null;
  partial_coverage: boolean;
}

export interface BatchComparisonResult {
  experiment_run_id: string;
  coverage: ComparisonCoverage;
  selected_scenario: SelectedScenarioComparison | null;
  summary: ComparisonStrategySummary[];
  rows: ComparisonRow[];
}

export interface ComparisonJob {
  job_id: string;
  experiment_run_id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: ComparisonProgress;
  result: BatchComparisonResult | null;
  message: string | null;
}
