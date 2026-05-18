import logging
import os
from datetime import datetime

import httpx
from celery import Task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.utils.signing import generate_signature
from app.worker.celery_app import celery_app
from app.worker.dlq import send_to_dlq

logger = logging.getLogger(__name__)

MAX_RETRIES = 5

# Module-level sync engine (created lazily so tests can patch DATABASE_URL first).
_sync_engine = None
_SyncSession = None


def _get_sync_session():
    global _sync_engine, _SyncSession
    if _sync_engine is None:
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:password@localhost:5432/webhooks",
        )
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        _sync_engine = create_engine(db_url, pool_pre_ping=True)
        _SyncSession = sessionmaker(bind=_sync_engine)
    return _SyncSession()


def _update_delivery_log(
    event_id: str,
    subscriber_id: int,
    event_type: str,
    payload: dict,
    status: str,
    attempts: int,
    error_message: str | None,
) -> None:
    """Upsert a delivery log row synchronously (called from Celery worker)."""
    from app.db.models import DeliveryLog

    try:
        session = _get_sync_session()
        with session:
            log = (
                session.query(DeliveryLog)
                .filter_by(event_id=event_id, subscriber_id=subscriber_id)
                .first()
            )
            if log:
                log.status = status
                log.attempts = attempts
                log.last_attempt = datetime.utcnow()
                log.error_message = error_message
            else:
                log = DeliveryLog(
                    event_id=event_id,
                    subscriber_id=subscriber_id,
                    event_type=event_type,
                    payload=payload,
                    status=status,
                    attempts=attempts,
                    last_attempt=datetime.utcnow(),
                    error_message=error_message,
                )
                session.add(log)
            session.commit()
    except Exception:
        logger.exception("Failed to update delivery log for event %s", event_id)


@celery_app.task(bind=True, max_retries=MAX_RETRIES, name="deliver_event")
def deliver_event(
    self: Task,
    event_id: str,
    subscriber_id: int,
    subscriber_url: str,
    subscriber_secret: str,
    event_type: str,
    payload: dict,
) -> None:
    """Deliver a webhook event to a subscriber endpoint with exponential backoff."""
    attempt = self.request.retries + 1
    signature = generate_signature(payload, subscriber_secret)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": event_type,
        "X-Webhook-Delivery-ID": event_id,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(subscriber_url, json=payload, headers=headers)
            response.raise_for_status()

        _update_delivery_log(
            event_id, subscriber_id, event_type, payload, "success", attempt, None
        )
        logger.info("Delivered event %s to subscriber %s", event_id, subscriber_id)

    except Exception as exc:
        logger.warning(
            "Delivery failed for event %s (attempt %d): %s", event_id, attempt, exc
        )

        if self.request.retries >= MAX_RETRIES - 1:
            _update_delivery_log(
                event_id, subscriber_id, event_type, payload, "dead_letter", attempt, str(exc)
            )
            send_to_dlq(event_id, subscriber_id, event_type, payload, str(exc))
            return

        _update_delivery_log(
            event_id, subscriber_id, event_type, payload, "failed", attempt, str(exc)
        )
        countdown = 2 ** self.request.retries
        raise self.retry(exc=exc, countdown=countdown)
