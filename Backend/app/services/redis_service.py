import redis
from app.core.config import settings

redis_client = redis.Redis(host=settings.REDIS_ENDPOINT.split(":")[0], port=6379)