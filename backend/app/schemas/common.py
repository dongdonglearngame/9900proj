from typing import Literal

from pydantic import BaseModel, ConfigDict

ChoiceLetter = Literal["A", "B", "C", "D"]
ChoiceMap = dict[ChoiceLetter, str]
OptionScoreMap = dict[ChoiceLetter, float | None]


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ModelInfo(APIModel):
    id: str
    name: str
    available: bool


class ModelsResponse(APIModel):
    models: list[ModelInfo]
