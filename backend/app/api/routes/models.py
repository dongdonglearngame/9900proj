from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import ModelInfo, ModelsResponse

router = APIRouter()


@router.get("", response_model=ModelsResponse)
def list_models() -> ModelsResponse:
    settings = get_settings()
    return ModelsResponse(
        models=[
            ModelInfo(
                id=settings.default_model,
                name="Llama 3.2 3B",
                available=settings.use_mock_llm,
            ),
            ModelInfo(id="qwen2.5:3b", name="Qwen2.5 3B", available=False),
            ModelInfo(id="phi3:mini", name="Phi-3 Mini", available=False),
        ]
    )
