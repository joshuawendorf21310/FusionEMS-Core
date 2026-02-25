import os
class Settings:
    ENV = os.getenv("ENV", "dev")
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    REDIS_ENDPOINT = os.getenv("REDIS_ENDPOINT", "")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
    COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "")

settings = Settings()