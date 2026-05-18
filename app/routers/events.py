import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Subscriber
from app.models.event import EventCreate, EventResponse
from app.worker.tasks import deliver_event

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/", response_model=EventResponse)
async def ingest_event(event: EventCreate, db: AsyncSession = Depends(get_db)):
    event_id = str(uuid.uuid4())
    queued_at = datetime.utcnow()

    result = await db.execute(select(Subscriber).where(Subscriber.active.is_(True)))
    subscribers = result.scalars().all()

    for subscriber in subscribers:
        if event.event_type in (subscriber.events or []):
            deliver_event.delay(
                event_id=event_id,
                subscriber_id=subscriber.id,
                subscriber_url=subscriber.url,
                subscriber_secret=subscriber.secret,
                event_type=event.event_type,
                payload=event.payload,
            )

    return EventResponse(
        id=event_id,
        event_type=event.event_type,
        payload=event.payload,
        queued_at=queued_at,
    )
