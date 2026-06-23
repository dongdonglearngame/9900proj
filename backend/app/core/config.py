from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    use_mock_llm: bool = True
    database_url: str = "sqlite:///./p18_dev.db"
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "llama3.2:3b"
    target_prompt_version: str = "target-v1-chat-nofoil"
    top_logprobs: int = 20
    target_num_predict: int = 4
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
