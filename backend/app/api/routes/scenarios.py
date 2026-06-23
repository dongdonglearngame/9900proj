from fastapi import APIRouter, Query

from app.repositories.scenario_repo import ScenarioRepository
from app.schemas.scenario import ScenariosResponse

router = APIRouter()
scenario_repo = ScenarioRepository()


@router.get("", response_model=ScenariosResponse)
def list_scenarios(
    task_type: str | None = Query(default=None),
    dimension: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ScenariosResponse:
    return scenario_repo.list_scenarios(
        task_type=task_type,
        dimension=dimension,
        limit=limit,
        offset=offset,
    )
