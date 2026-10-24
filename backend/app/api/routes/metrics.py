from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.profile import MetricsUpload
from app.services import profile as profile_service
from app.api.deps import get_db

router = APIRouter()


@router.post("/{profile_id}")
def upload_metrics(profile_id: int, payload: MetricsUpload, db: Session = Depends(get_db)):
    profile = profile_service.get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    items = profile_service.add_metrics(db, profile_id, [m.model_dump() for m in payload.metrics])
    return {"count": len(items)}
