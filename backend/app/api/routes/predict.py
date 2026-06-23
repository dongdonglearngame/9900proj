from fastapi import APIRouter

from app.schemas.predict import PredictionResponse, PredictRequest
from app.services.prediction_service import get_prediction_service

router = APIRouter()


@router.post("", response_model=PredictionResponse)
def predict(request: PredictRequest) -> PredictionResponse:
    return get_prediction_service().predict(request)
