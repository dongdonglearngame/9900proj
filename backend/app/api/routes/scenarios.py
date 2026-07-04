from fastapi import APIRouter, Query

from app.repositories.factory import get_scenario_repository
from app.schemas.scenario import ScenariosResponse

router = APIRouter()


@router.get("", response_model=ScenariosResponse)
def list_scenarios(
    task_type: str | None = Query(default=None),
    dimension: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ScenariosResponse:
    return get_scenario_repository().list_scenarios(
        task_type=task_type,
        dimension=dimension,
        limit=limit,
        offset=offset,
    )
