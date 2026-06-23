# Strategy Interface

New strategies implement `CounterfactualStrategy` in `backend/app/strategies/base.py`.

Required steps:

1. Add `backend/app/strategies/sN_name.py`.
2. Implement `generate(request, target_predict)`.
3. Return `CounterfactualResult` with `success`, `not_found`, or `failed`.
4. Register the strategy in `backend/app/strategies/registry.py`.
5. Add focused tests.

Rules:

- `target_predict(scenario, choices, model)` must be the only verification path.
- The strategy may see `foil`, but the target prompt must not.
- Respect `budget`.
- Record failed attempts when useful.
- Do not compute shared metrics inside the strategy.
