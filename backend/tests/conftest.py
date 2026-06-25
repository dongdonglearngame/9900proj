import os


def pytest_configure() -> None:
    os.environ["APP_ENV"] = "test"
    os.environ["USE_MOCK_LLM"] = "true"

    from app.core.config import get_settings
    from app.services.prediction_service import get_prediction_service

    get_settings.cache_clear()
    get_prediction_service.cache_clear()
