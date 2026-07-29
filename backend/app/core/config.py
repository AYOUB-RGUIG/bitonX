"""Application settings for the backend foundation."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BitonX Quant API"
    app_version: str = "0.2.0"
    environment: str = Field(default="development", alias="BITONX_ENV")
    log_level: str = Field(default="INFO", alias="BITONX_LOG_LEVEL")
    database_url: str = Field(
        default="postgresql+psycopg://bitonx:bitonx_dev_password@localhost:5432/bitonx",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    rabbitmq_url: str = Field(
        default="amqp://bitonx:bitonx_dev_password@localhost:5672//",
        alias="RABBITMQ_URL",
    )
    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="bitonx", alias="MINIO_ROOT_USER")
    minio_secret_key: str = Field(default="bitonx_dev_password", alias="MINIO_ROOT_PASSWORD")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")
    minio_bucket_uploads: str = Field(default="bitonx-uploads", alias="MINIO_BUCKET_UPLOADS")
    minio_bucket_artifacts: str = Field(default="bitonx-artifacts", alias="MINIO_BUCKET_ARTIFACTS")
    minio_bucket_reports: str = Field(default="bitonx-reports", alias="MINIO_BUCKET_REPORTS")
    max_upload_size_bytes: int = Field(default=104_857_600, alias="MAX_UPLOAD_SIZE_BYTES")
    jwt_secret_key: str = Field(default="change-me-in-real-environments", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")


@lru_cache
def get_settings() -> Settings:
    """Return cached backend settings."""
    return Settings()
