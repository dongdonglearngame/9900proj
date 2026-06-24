from app.strategies.base import CounterfactualResult, TargetModel


class IdentityPostProcessor:
    def process(
        self,
        raw_result: CounterfactualResult,
        *,
        scenario: str,
        choices: dict[str, str],
        model: TargetModel,
        foil: str,
        budget: int,
    ) -> CounterfactualResult:
        _ = scenario
        _ = choices
        _ = model
        _ = foil
        _ = budget
        return raw_result
