"""AI package settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    """Runtime settings for AI workers and tools."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="development", alias="BITONX_AI_ENV")
    log_level: str = Field(default="INFO", alias="BITONX_AI_LOG_LEVEL")
    model_dir: Path = Field(default=Path("models"), alias="BITONX_MODEL_DIR")
    checkpoint_dir: Path = Field(default=Path("checkpoints"), alias="BITONX_CHECKPOINT_DIR")
    dataset_dir: Path = Field(default=Path("../datasets"), alias="BITONX_DATASET_DIR")
    mlflow_tracking_uri: str = Field(
        default="http://localhost:5000",
        alias="MLFLOW_TRACKING_URI",
    )


@lru_cache
def get_ai_settings() -> AISettings:
    """Return cached AI package settings."""
    return AISettings()

