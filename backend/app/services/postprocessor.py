from app.strategies.base import CounterfactualRequest, CounterfactualResult, TargetPredictFn


class IdentityPostProcessor:
    def process(
        self,
        raw_result: CounterfactualResult,
        request: CounterfactualRequest,
        target_predict: TargetPredictFn,
    ) -> CounterfactualResult:
        _ = request
        _ = target_predict
        return raw_result
