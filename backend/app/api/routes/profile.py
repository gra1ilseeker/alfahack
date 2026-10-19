from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.profile import ProfileCreate, ProfileResponse
from app.services import profile as profile_service
from app.api.deps import get_db

router = APIRouter()


@router.post("/", response_model=ProfileResponse)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    profile = profile_service.create_profile(
        db,
        user_email=payload.user_email,
        password=payload.password,
        industry=payload.industry,
        revenue_band=payload.revenue_band,
        employees=payload.employees,
        goals=payload.goals,
    )
    return profile


@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = profile_service.get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
