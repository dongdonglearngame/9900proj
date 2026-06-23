from fastapi import APIRouter

router = APIRouter()


@router.get("/summary")
def get_dashboard_summary() -> dict[str, list[dict[str, str | int | float]]]:
    # TODO(P18-METRICS-1): aggregate per-strategy metrics from stored results
    #   (flip_rate, avg edit distance, avg search calls, not_found_count, ...).
    return {"strategies": []}
