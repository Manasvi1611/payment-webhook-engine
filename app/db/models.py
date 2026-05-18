from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.types import JSON
from app.db.database import Base


class Subscriber(Base):
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    events = Column(JSON, nullable=False)
    secret = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, nullable=False, index=True)
    subscriber_id = Column(Integer, ForeignKey("subscribers.id"), nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, default="pending")
    attempts = Column(Integer, default=0)
    last_attempt = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
