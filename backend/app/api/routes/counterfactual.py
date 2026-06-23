from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas.counterfactual import (
    CounterfactualCreateRequest,
    CounterfactualCreateResponse,
    CounterfactualJobResponse,
    StrategyListResponse,
)
from app.services.counterfactual_service import CounterfactualService
from app.strategies.registry import list_strategy_infos

router = APIRouter()
counterfactual_service = CounterfactualService()


@router.get("/strategies", response_model=StrategyListResponse)
def list_strategies() -> StrategyListResponse:
    return StrategyListResponse(strategies=list_strategy_infos())


@router.post("", response_model=CounterfactualCreateResponse)
def create_counterfactual_job(
    request: CounterfactualCreateRequest,
    background_tasks: BackgroundTasks,
) -> CounterfactualCreateResponse:
    response = counterfactual_service.create_job(request)
    background_tasks.add_task(counterfactual_service.run_job, response.job_id, request)
    return response


@router.get("/jobs/{job_id}", response_model=CounterfactualJobResponse)
def get_counterfactual_job(job_id: str) -> CounterfactualJobResponse:
    job = counterfactual_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job_id: {job_id}")
    return job
