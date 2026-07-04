import os


def pytest_configure() -> None:
    os.environ["APP_ENV"] = "test"
    os.environ["REPO_BACKEND"] = "memory"
    os.environ["USE_MOCK_LLM"] = "true"

    from app.core.config import get_settings
    from app.repositories.factory import clear_repository_caches
    from app.services.prediction_service import get_prediction_service

    get_settings.cache_clear()
    clear_repository_caches()
    get_prediction_service.cache_clear()
