import argparse

from app.schemas.comparison import ComparisonCreateRequest
from app.services.batch_comparison_service import BatchComparisonService


def _strategy_ids(value: str) -> list[str]:
    strategy_ids = [item.strip() for item in value.split(",") if item.strip()]
    if not strategy_ids:
        raise argparse.ArgumentTypeError("at least one strategy ID is required")
    if len(set(strategy_ids)) != len(strategy_ids):
        raise argparse.ArgumentTypeError("strategy IDs must not contain duplicates")
    return strategy_ids


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a fixed-subset counterfactual strategy comparison."
    )
    parser.add_argument("--task_type", "--task-type", dest="task_type", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--model", required=True)
    parser.add_argument("--strategies", required=True, type=_strategy_ids)
    parser.add_argument("--budget", type=int, default=20)
    parser.add_argument("--dimension")
    parser.add_argument(
        "--foil-mode",
        choices=("single", "all_non_original"),
        default="single",
    )
    args = parser.parse_args()

    request = ComparisonCreateRequest(
        model=args.model,
        strategy_ids=args.strategies,
        task_type=args.task_type,
        dimension=args.dimension,
        limit=args.limit,
        offset=args.offset,
        budget=args.budget,
        foil_mode=args.foil_mode,
    )
    service = BatchComparisonService()
    try:
        created = service.create_job(request)
    except ValueError as exc:
        raise SystemExit(f"invalid comparison request: {exc}") from exc
    service.run_job(created.job_id, request)
    job = service.get_job(created.job_id)
    if job is None:
        raise SystemExit("comparison job disappeared before completion")
    print(job.model_dump_json(indent=2))
    if job.status != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
