from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import DeliveryLog, Subscriber
from app.models.delivery import DeliveryLogResponse
from app.worker.tasks import deliver_event

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.get("/", response_model=list[DeliveryLogResponse])
async def list_deliveries(
    subscriber_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(DeliveryLog).order_by(DeliveryLog.created_at.desc()).limit(limit)
    if subscriber_id is not None:
        query = query.where(DeliveryLog.subscriber_id == subscriber_id)
    if status is not None:
        query = query.where(DeliveryLog.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{delivery_id}/replay")
async def replay_delivery(delivery_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DeliveryLog).where(DeliveryLog.id == delivery_id)
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    sub_result = await db.execute(
        select(Subscriber).where(Subscriber.id == delivery.subscriber_id)
    )
    subscriber = sub_result.scalar_one_or_none()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    deliver_event.delay(
        event_id=delivery.event_id,
        subscriber_id=subscriber.id,
        subscriber_url=subscriber.url,
        subscriber_secret=subscriber.secret,
        event_type=delivery.event_type,
        payload=delivery.payload,
    )

    return {"message": "Delivery queued for replay", "event_id": delivery.event_id}
