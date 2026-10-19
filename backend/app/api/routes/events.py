from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.event import EventCreate
from app.services import event as event_service
from app.api.deps import get_db

router = APIRouter()


@router.post("/")
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    evt = event_service.log_event(db, payload.profile_id, payload.event_type, payload.payload)
    return {"id": evt.id}
