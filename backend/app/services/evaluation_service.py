class EvaluationService:
    """Baseline target-model accuracy over loaded questions (P18-3).

    TODO(P18-EVAL-1): implement run_baseline — iterate the loaded questions for the
      given model/task_type, predict each through the frozen harness (reusing the
      prediction cache), and aggregate accuracy overall and by dimension.
    """

    def run_baseline(self, model: str, task_type: str) -> dict[str, object]:
        return {
            "model": model,
            "task_type": task_type,
            "status": "not_implemented",
        }
