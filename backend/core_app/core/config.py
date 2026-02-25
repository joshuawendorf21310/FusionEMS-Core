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

    redis_url: str = Field(default="redis://localhost:6379/0")
    s3_bucket_docs: str = Field(default="")
    s3_bucket_exports: str = Field(default="")

    # Integrations (set via environment or injected from Secrets Manager)
    openai_api_key: str = Field(default="")
    stripe_secret_key: str = Field(default="")
    stripe_webhook_secret: str = Field(default="")
    telnyx_api_key: str = Field(default="")
    telnyx_from_number: str = Field(default="")
    telnyx_messaging_profile_id: str = Field(default="")
    officeally_sftp_host: str = Field(default="")
    officeally_sftp_port: int = Field(default=22)
    officeally_sftp_username: str = Field(default="")
    officeally_sftp_password: str = Field(default="")
    officeally_sftp_remote_dir: str = Field(default="/")
    

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
