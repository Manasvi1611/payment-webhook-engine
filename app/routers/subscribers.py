from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Subscriber
from app.models.event import SubscriberCreate, SubscriberResponse, SubscriberUpdate

router = APIRouter(prefix="/subscribers", tags=["subscribers"])


@router.post("/", response_model=SubscriberResponse)
async def create_subscriber(
    subscriber: SubscriberCreate, db: AsyncSession = Depends(get_db)
):
    db_sub = Subscriber(
        name=subscriber.name,
        url=subscriber.url,
        events=subscriber.events,
        secret=subscriber.secret,
    )
    db.add(db_sub)
    await db.commit()
    await db.refresh(db_sub)
    return db_sub


@router.get("/", response_model=list[SubscriberResponse])
async def list_subscribers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscriber).order_by(Subscriber.id))
    return result.scalars().all()


@router.get("/{subscriber_id}", response_model=SubscriberResponse)
async def get_subscriber(subscriber_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Subscriber).where(Subscriber.id == subscriber_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return sub


@router.patch("/{subscriber_id}", response_model=SubscriberResponse)
async def update_subscriber(
    subscriber_id: int, update: SubscriberUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Subscriber).where(Subscriber.id == subscriber_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    if update.name is not None:
        sub.name = update.name
    if update.url is not None:
        sub.url = update.url
    if update.events is not None:
        sub.events = update.events
    if update.secret is not None:
        sub.secret = update.secret
    await db.commit()
    await db.refresh(sub)
    return sub


@router.patch("/{subscriber_id}/deactivate", response_model=SubscriberResponse)
async def deactivate_subscriber(
    subscriber_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Subscriber).where(Subscriber.id == subscriber_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    sub.active = False
    await db.commit()
    await db.refresh(sub)
    return sub


@router.delete("/{subscriber_id}", status_code=204)
async def delete_subscriber(subscriber_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Subscriber).where(Subscriber.id == subscriber_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    await db.delete(sub)
    await db.commit()
