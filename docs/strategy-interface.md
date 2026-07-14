# Strategy Interface

New strategies implement `CounterfactualStrategy` in `backend/app/strategies/base.py`.

Required interface:

```python
def generate(
    self,
    scenario: str,
    choices: dict[str, str],
    model: TargetModel,
    foil: str,
    budget: int,
    proposer: Proposer,
) -> CounterfactualResult:
    ...
```

`model` is a frozen target-model harness. Strategies must call
`model.target_predict(candidate_scenario, choices)` to verify candidates. They
must not import or instantiate LLM clients, call `/predict`, build target
prompts, change decoding settings, or pass the foil into target prediction.

`proposer` is the injected generative search-agent harness. It may see the foil
and can propose candidate scenario rewrites, but it is separate from the frozen
target harness and must not use the prediction cache.

The target (`model.target_predict`) and proposer harness methods such as
`proposer.propose` and `proposer.infill` are the injected search capabilities. Adding
a strategy that reuses these requires no
service or route changes. Strategies still must not import or instantiate LLM
clients, build target prompts, change decoding, or leak the foil into the target.

Required steps:

1. Add `backend/app/strategies/sN_name.py`.
2. Define a no-argument class that subclasses `CounterfactualStrategy`.
3. Set a unique `id` and human-readable `name`.
4. Implement `generate(scenario, choices, model, foil, budget, proposer)`.
5. Return `CounterfactualResult` with `success`, `not_found`, or `failed`.
6. Add focused tests.

The registry auto-discovers strategy modules under `backend/app/strategies`.
Adding a new strategy that uses the existing target/proposer ports must not
require changes to service or API route code.

Rules:

- `model.target_predict(scenario, choices)` must be the only target-model path.
- Methods exposed by the injected proposer harness must be the only generative paths.
- The strategy may see `foil`, but the target prompt must not.
- Respect `budget`.
- Record failed attempts when useful.
- Report candidate guard outcomes through the shared proposer diagnostics helper.
- Do not compute shared metrics inside the strategy.
