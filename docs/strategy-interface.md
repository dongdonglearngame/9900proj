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
and can propose either full candidate rewrites through `propose(...)` or typed,
single-span concept interventions through `propose_concept_edits(...)`. It is
separate from the frozen target harness and must not use the prediction cache.

The target (`model.target_predict`) and the methods exposed by the injected
`proposer` harness are the two search capabilities. Adding a strategy that reuses
these requires no new strategy dispatch or model-access path. Shared result schema
and metadata mapping may still be extended. Strategies must not import or
instantiate LLM clients, build target prompts, change decoding, or leak the foil
into the target.

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
- `proposer.propose(...)` and `proposer.propose_concept_edits(...)` are the only
  generative proposer paths.
- The strategy may see `foil`, but the target prompt must not.
- Respect `budget`.
- Record failed attempts when useful.
- Do not compute shared metrics inside the strategy.

S6 uses causal-inspired concept interventions rather than claiming formally
identified causal effects. Each successful S6 result carries the final concept
class and exact source/replacement spans. A postprocessor that changes those
spans must update the metadata or the service falls back to the verified raw
result.
