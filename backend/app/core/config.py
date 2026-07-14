from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    repo_backend: Literal["memory", "sqlite"] = "memory"
    use_mock_llm: bool = True
    database_url: str = "sqlite:///./p18_dev.db"
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "llama3.2:3b"
    target_prompt_version: str = "target-v2-chat-dynamic-choices"
    top_logprobs: int = 20
    target_num_predict: int = 4
    target_temperature: float = 0.0
    proposer_model: str = "llama3.2:3b"
    proposer_temperature: float = 0.7
    proposer_seed: int = 0
    proposer_num_predict: int = 512
    proposer_candidates_per_round: int = 4
    proposer_max_rounds: int = 2
    proposer_max_changed_fraction: float = 0.6
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
