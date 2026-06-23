from app.strategies.base import (
    CounterfactualRequest,
    CounterfactualResult,
    CounterfactualStrategy,
    TargetPredictFn,
)


class S1WordGreedyStrategy(CounterfactualStrategy):
    """S1 - word-level greedy baseline (the MVP strategy every other strategy is compared against).

    TODO(P18-CF-3): implement `generate`. See plan section 10.2:
      1. generate small candidate edits from the scenario (content-word deletion,
         adjective/adverb weakening, time-phrase substitution, emotion-intensity
         substitution, small controlled insertions, local synonym/antonym swaps)
      2. dedupe candidates
      3. for each candidate, stop if search_calls == request.budget, otherwise call
         target_predict(candidate, choices, model) and check prediction.answer == request.foil
      4. return success on the first flip, else not_found (not an exception)
    The goal is transparent / reproducible, not clever.
    """

    id = "s1_word_greedy"
    name = "S1 Word-level Greedy"

    def generate(
        self,
        request: CounterfactualRequest,
        target_predict: TargetPredictFn,
    ) -> CounterfactualResult:
        raise NotImplementedError("S1 word-level greedy strategy not implemented yet (P18-CF-3)")
