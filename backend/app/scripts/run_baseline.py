import argparse
import json

from app.services.evaluation_service import EvaluationService


def main() -> None:
    parser = argparse.ArgumentParser(description="Run baseline target-model evaluation.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--task_type", required=True)
    args = parser.parse_args()
    result = EvaluationService().run_baseline(model=args.model, task_type=args.task_type)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
