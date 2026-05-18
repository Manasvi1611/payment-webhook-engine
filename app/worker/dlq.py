import json
import logging
import os

import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DLQ_KEY = "webhook:dlq"


def send_to_dlq(
    event_id: str,
    subscriber_id: int,
    event_type: str,
    payload: dict,
    error: str,
) -> None:
    """Push a permanently-failed delivery onto the dead-letter queue."""
    r = redis.from_url(REDIS_URL)
    entry = {
        "event_id": event_id,
        "subscriber_id": subscriber_id,
        "event_type": event_type,
        "payload": payload,
        "error": error,
    }
    r.rpush(DLQ_KEY, json.dumps(entry))
    logger.warning("Event %s moved to DLQ for subscriber %s", event_id, subscriber_id)


def get_dlq_entries(limit: int = 100) -> list[dict]:
    """Return up to *limit* entries from the DLQ (oldest first)."""
    r = redis.from_url(REDIS_URL)
    raw = r.lrange(DLQ_KEY, 0, limit - 1)
    return [json.loads(item) for item in raw]


def pop_dlq_entry() -> dict | None:
    """Remove and return the oldest DLQ entry, or None if empty."""
    r = redis.from_url(REDIS_URL)
    raw = r.lpop(DLQ_KEY)
    return json.loads(raw) if raw else None
