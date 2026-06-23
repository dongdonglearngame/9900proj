# Project Handoff

This document records the project constraints and architecture decisions that should
stay stable while feature teams implement the TODO stubs.

## Project Summary

Build a local web tool for counterfactual explanations on EmoBench multiple-choice
tasks. A user selects a scenario, gets the model's current answer, chooses a foil
answer, and runs a search strategy that tries to make a small meaningful edit to
the scenario so the model changes its answer to the foil.

Failed searches are valid results and should be recorded for comparison.

## Team And Client Context

- Client: Dr Thao Le, UNSW.
- Team: 9900-F09C-ALMOND.
- Stack: React, FastAPI, Ollama, SQLite or CSV-backed data access.
- Main deliverable: a full-stack tool with a shared harness, pluggable strategies,
  explanation metrics, and comparison views.

## Hard Constraints

- Black-box access only through local inference.
- No fine-tuning.
- No paid cloud APIs or hosted model services.
- Prefer free local open-source models in the 3B class.
- Must remain feasible on CPU laptops without dedicated GPUs.
- No large-scale training and no HPC dependency.

## Task Definition

- Dataset: EmoBench multiple-choice emotional reasoning questions.
- Question format: four choices, one selected answer.
- Flip target: the final argmax answer must become the user-selected foil.
- A budget-exhausted search that does not find a flip is a normal result, not a
  server error.

## Example

Scenario:

```text
Regina's best friend recently broke up with her longtime partner and is texting
Regina in the middle of the night expressing feelings of loneliness.
```

Choices:

```text
A. Ignore the texts and continue sleeping
B. Tell her friend to seek professional help
C. Stay up and lend a listening ear
D. Ask her friend to stop texting at night
```

The original model answer is A. If the foil is C, a useful counterfactual might
change "middle of the night" to "early evening". The explanation is that the model
was relying on the timing of the message, not only on the friend's emotional state.

## Architecture

```text
React frontend
  -> FastAPI controller layer
  -> service layer
  -> repository layer
  -> local model harness
```

Core service boundaries:

- PredictionService wraps the frozen harness and prediction cache.
- CounterfactualService runs one strategy and then applies shared post-processing.
- EvaluationService owns baseline and comparison metrics.
- Repository classes hide the persistence backend.

## Shared Harness Rule

All strategies must call the same frozen prediction harness. The harness must use
a fixed prompt version, deterministic decoding, constrained parsing, and a stable
cache key. Strategies may propose edits, but they must not decide whether a flip
succeeded. Only the shared harness decides that.

## Strategy Scope

The strategy interface is intentionally narrow. Strategies differ only in how they
propose candidate edits. Minimality checks, fluency checks, diff generation, scoring,
and dashboard aggregation should stay shared.

Initial strategy priorities:

1. S1 word-level greedy baseline.
2. One or two additional strategies if capacity allows.
3. Record negative results when a strategy fails within budget.

## Persistence Notes

SQLite is useful for caching predictions, jobs, counterfactuals, and metrics, but
the client accepts simpler CSV-backed data loading if time is tight. The skeleton
keeps the SQLModel table definitions but leaves repository wiring as TODO work.

## Sprint Direction

- Sprint 1: finish the harness, data loading, baseline evaluation, S1 strategy,
  and a single-page demo workflow.
- Sprint 2: add more strategies, comparison metrics, multi-model support, and
  async job handling.
- Sprint 3: complete dashboard views, deployment notes, and final demo polish.

## Repository Workflow

- Work through feature branches and pull requests.
- Keep commits small and tied to issues where possible.
- Add tests for each implemented TODO.
- Preserve the scaffold contract unless the team agrees to a contract change.
