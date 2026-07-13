from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas.comparison import (
    ComparisonCreateRequest,
    ComparisonCreateResponse,
    ComparisonJobResponse,
)
from app.services.batch_comparison_service import BatchComparisonService

router = APIRouter()
comparison_service = BatchComparisonService()


@router.post("", response_model=ComparisonCreateResponse)
def create_comparison_job(
    request: ComparisonCreateRequest,
    background_tasks: BackgroundTasks,
) -> ComparisonCreateResponse:
    response = comparison_service.create_job(request)
    background_tasks.add_task(comparison_service.run_job, response.job_id, request)
    return response


@router.get("/jobs/{job_id}", response_model=ComparisonJobResponse)
def get_comparison_job(job_id: str) -> ComparisonJobResponse:
    job = comparison_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown comparison job_id: {job_id}")
    return job
