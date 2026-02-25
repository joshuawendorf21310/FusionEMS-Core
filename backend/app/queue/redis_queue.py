import redis
import json
from app.core.config import settings

redis_client = redis.Redis.from_url(f"redis://{settings.REDIS_ENDPOINT}")

def enqueue_task(name: str, payload: dict):
    redis_client.rpush("task_queue", json.dumps({"task": name, "payload": payload}))

def dequeue_task():
    task = redis_client.lpop("task_queue")
    return json.loads(task) if task else None