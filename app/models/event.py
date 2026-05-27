from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator

VALID_EVENT_TYPES = frozenset(
    ["payment.success", "payment.failed", "payment.refunded"]
)


class EventCreate(BaseModel):
    event_type: Literal["payment.success", "payment.failed", "payment.refunded"]
    payload: dict[str, Any]


class EventResponse(BaseModel):
    id: str
    event_type: str
    payload: dict[str, Any]
    queued_at: datetime


class SubscriberCreate(BaseModel):
    name: str
    url: str
    events: list[str]
    secret: str

    @field_validator("events")
    @classmethod
    def events_must_be_valid(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_EVENT_TYPES
        if invalid:
            raise ValueError(f"Unknown event types: {invalid}")
        return v


class SubscriberUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[list[str]] = None
    secret: Optional[str] = None

    @field_validator("events")
    @classmethod
    def events_must_be_valid(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        invalid = set(v) - VALID_EVENT_TYPES
        if invalid:
            raise ValueError(f"Unknown event types: {invalid}")
        return v


class SubscriberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    events: list[str]
    active: bool
    created_at: datetime
