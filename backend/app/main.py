from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import counterfactual, dashboard, health, models, predict, scenarios
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    api = FastAPI(title="P18 Explainable LLM Backend")

    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api.include_router(health.router, prefix="/health", tags=["health"])
    api.include_router(models.router, prefix="/models", tags=["models"])
    api.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
    api.include_router(predict.router, prefix="/predict", tags=["predict"])
    api.include_router(counterfactual.router, prefix="/counterfactual", tags=["counterfactual"])
    api.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
    return api


app = create_app()
