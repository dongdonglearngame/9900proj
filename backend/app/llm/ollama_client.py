from app.harness.target_predict import PredictionResult


class OllamaClient:
    """Frozen target-model client (real inference path).

    TODO(P18-HARNESS-1): implement the native Ollama `/api/chat` call here.
      - messages = build_target_messages(scenario, choices)  (NEVER include the foil)
      - stream=False, options.temperature=0, options.num_predict=settings.target_num_predict
      - logprobs=True, top_logprobs=settings.top_logprobs
      - parse the answer letter (harness.parser.parse_answer_letter)
      - extract per-option logprobs (harness.logprobs.extract_option_logprobs)
      - retry once on parse failure before returning status="parse_failed"
    Return a PredictionResult. See plan section 7.
    """

    def predict(self, scenario: str, choices: dict[str, str], model: str) -> PredictionResult:
        raise NotImplementedError("Ollama harness not implemented yet (P18-HARNESS-1)")
