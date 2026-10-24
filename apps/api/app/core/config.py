from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    database_url: SecretStr
    local_only: Literal[True] = True
    data_profile: Literal["demo_seed", "approved_public", "real_demo"] = "demo_seed"
    inference_url: str = "http://127.0.0.1:19090"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )
    cookie_secure: bool = False

    @field_validator("local_only", mode="before")
    @classmethod
    def offline_required(cls, value: object) -> bool:
        if value is True or isinstance(value, str) and value.lower() == "true":
            return True
        raise ValueError("LOCAL_ONLY must be true in the baseline")

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use postgresql+psycopg")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
