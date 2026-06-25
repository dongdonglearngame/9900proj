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
) -> CounterfactualResult:
    ...
```

`model` is a frozen target-model harness. Strategies must call
`model.target_predict(candidate_scenario, choices)` to verify candidates. They
must not import or instantiate LLM clients, call `/predict`, build target
prompts, change decoding settings, or pass the foil into target prediction.

Required steps:

1. Add `backend/app/strategies/sN_name.py`.
2. Define a no-argument class that subclasses `CounterfactualStrategy`.
3. Set a unique `id` and human-readable `name`.
4. Implement `generate(scenario, choices, model, foil, budget)`.
5. Return `CounterfactualResult` with `success`, `not_found`, or `failed`.
6. Add focused tests.

The registry auto-discovers strategy modules under `backend/app/strategies`.
Adding a new strategy must not require changes to service or API route code.

Rules:

- `model.target_predict(scenario, choices)` must be the only target-model path.
- The strategy may see `foil`, but the target prompt must not.
- Respect `budget`.
- Record failed attempts when useful.
- Do not compute shared metrics inside the strategy.
