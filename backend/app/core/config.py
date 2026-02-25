import os
from functools import lru_cache

class Settings:
    ENV: str = os.getenv("ENV", "prod")
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    REDIS_ENDPOINT: str = os.getenv("REDIS_ENDPOINT")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    COGNITO_USER_POOL_ID: str = os.getenv("COGNITO_USER_POOL_ID")
    COGNITO_CLIENT_ID: str = os.getenv("COGNITO_CLIENT_ID")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY")

@lru_cache
def get_settings():
    return Settings()