from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("")
def health_check() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "use_mock_llm": settings.use_mock_llm,
    }
