"""
Redis Queue Manager — handles all task queue operations.
Named queues for each agent type + failed_queue dead-letter.
"""

import json
import os
import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Synchronous Redis client (used by Celery workers and queue ops)
_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        url = REDIS_URL
        if url.startswith("rediss://") and "ssl_cert_reqs" not in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}ssl_cert_reqs=none"
        _redis_client = redis.from_url(url, decode_responses=True)
    return _redis_client


# ─── Queue Names ──────────────────────────────────────────────────────────────

QUEUES = {
    "planner": "planner_queue",
    "retriever": "retriever_queue",
    "analyzer": "analyzer_queue",
    "writer": "writer_queue",
    "validator": "validator_queue",
    "failed": "failed_queue",
}


# ─── Queue Operations ─────────────────────────────────────────────────────────

def push_task(agent: str, payload: dict):
    """Push a task payload to the appropriate agent queue."""
    queue_name = QUEUES.get(agent, f"{agent}_queue")
    r = get_redis()
    r.rpush(queue_name, json.dumps(payload))


def pop_task(agent: str) -> dict | None:
    """Non-blocking pop from agent queue. Returns None if empty."""
    queue_name = QUEUES.get(agent, f"{agent}_queue")
    r = get_redis()
    item = r.lpop(queue_name)
    return json.loads(item) if item else None


def push_to_dead_letter(payload: dict):
    """Move a permanently failed task to the dead letter queue."""
    r = get_redis()
    r.rpush(QUEUES["failed"], json.dumps(payload))


def get_queue_length(agent: str) -> int:
    """Get current queue depth for an agent."""
    queue_name = QUEUES.get(agent, f"{agent}_queue")
    r = get_redis()
    return r.llen(queue_name)


def get_all_queue_stats() -> dict:
    """Return length of all queues — used for monitoring."""
    r = get_redis()
    return {name: r.llen(queue) for name, queue in QUEUES.items()}


# ─── Progress Pub/Sub ─────────────────────────────────────────────────────────

def publish_progress(task_id: str, message: dict):
    """Publish a progress event to a task-specific Redis channel."""
    r = get_redis()
    r.publish(f"task:{task_id}:progress", json.dumps(message))


def subscribe_progress(task_id: str):
    """Return a pubsub subscriber for a task's progress channel."""
    r = get_redis()
    pubsub = r.pubsub()
    pubsub.subscribe(f"task:{task_id}:progress")
    return pubsub
