from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class DeliveryLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    subscriber_id: int
    event_type: str
    payload: dict[str, Any]
    status: str
    attempts: int
    last_attempt: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
