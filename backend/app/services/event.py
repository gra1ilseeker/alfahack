from sqlalchemy.orm import Session
from app.models import Event


def log_event(db: Session, profile_id: int | None, event_type: str, payload: dict | None = None) -> Event:
    event = Event(profile_id=profile_id, event_type=event_type, payload=payload)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
