from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "FusionEMS Core"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    database_url: str = Field(default="postgresql+psycopg://postgres:postgres@localhost:5432/fusionems")

    jwt_secret_key: str = Field(default="change-me")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
