from typing import Any, Optional
from pydantic import BaseModel


class EventCreate(BaseModel):
    profile_id: Optional[int] = None
    event_type: str
    payload: Optional[Any] = None
