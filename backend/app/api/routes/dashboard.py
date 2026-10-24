from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.dashboard import DashboardResponse
from app.services import dashboard as dashboard_service
from app.services import profile as profile_service
from app.api.deps import get_db

router = APIRouter()


@router.get("/{profile_id}", response_model=DashboardResponse)
def get_dashboard(profile_id: int, db: Session = Depends(get_db)):
    profile = profile_service.get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    result = dashboard_service.compute_dashboard(db, profile_id)
    return DashboardResponse(profile_id=profile_id, summary=result["summary"], stability_index=result["stability_index"])
