from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single server-side configuration boundary for MedLens."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    groq_api_key: Optional[str] = Field(default=None, validation_alias="GROQ_API_KEY")
    groq_model: str = Field(default="openai/gpt-oss-20b", validation_alias="GROQ_MODEL")
    database_url: str = Field(default="sqlite:///./medlens.db", validation_alias="DATABASE_URL")
    environment: str = Field(default="development", validation_alias="APP_ENV")
    ai_provider: str = Field(default="groq", validation_alias="MEDLENS_AI_PROVIDER")
    max_upload_size: int = Field(default=10 * 1024 * 1024, validation_alias="MAX_UPLOAD_SIZE")


def get_settings() -> Settings:
    return Settings()
