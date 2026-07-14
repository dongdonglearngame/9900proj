import argparse
from pathlib import Path

from app.schemas.comparison import ComparisonCreateRequest
from app.services.batch_comparison_service import BatchComparisonService


def _strategy_ids(value: str) -> list[str]:
    strategy_ids = [item.strip() for item in value.split(",") if item.strip()]
    if not strategy_ids:
        raise argparse.ArgumentTypeError("at least one strategy ID is required")
    if len(set(strategy_ids)) != len(strategy_ids):
        raise argparse.ArgumentTypeError("strategy IDs must not contain duplicates")
    return strategy_ids


def _question_ids(value: str) -> list[str]:
    question_ids = [item.strip() for item in value.split(",") if item.strip()]
    if not question_ids:
        raise argparse.ArgumentTypeError("at least one question ID is required")
    if len(set(question_ids)) != len(question_ids):
        raise argparse.ArgumentTypeError("question IDs must not contain duplicates")
    return question_ids


def _question_ids_file(path: Path) -> list[str]:
    values = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return _question_ids(",".join(values))


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
    parser.add_argument("--output", type=Path)
    subset_group = parser.add_mutually_exclusive_group()
    subset_group.add_argument(
        "--question-ids",
        type=_question_ids,
        help="Comma-separated fixed subset; overrides limit/offset selection.",
    )
    subset_group.add_argument(
        "--question-ids-file",
        type=Path,
        help="Text file containing one fixed question ID per line.",
    )
    parser.add_argument(
        "--foil-mode",
        choices=("single", "all_non_original"),
        default="single",
    )
    args = parser.parse_args()
    question_ids = (
        _question_ids_file(args.question_ids_file)
        if args.question_ids_file is not None
        else args.question_ids
    )

    request = ComparisonCreateRequest(
        model=args.model,
        strategy_ids=args.strategies,
        task_type=args.task_type,
        dimension=args.dimension,
        question_ids=question_ids,
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
    rendered = job.model_dump_json(indent=2)
    if args.output is not None:
        args.output.write_text(f"{rendered}\n", encoding="utf-8")
        print(f"wrote comparison result to {args.output}")
    else:
        print(rendered)
    if job.status != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
