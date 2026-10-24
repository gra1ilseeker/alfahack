from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import Profile, User
from app.schemas.profile import ProfileCreate, ProfileResponse
from app.services import profile as profile_service
from app.api.deps import get_db
from app.utils.security import verify_password

router = APIRouter()


@router.post("/", response_model=ProfileResponse)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.user_email).first()
    if existing:
        if not verify_password(payload.password, existing.password_hash):
            raise HTTPException(status_code=400, detail="User already exists")
        profile = db.query(Profile).filter(Profile.user_id == existing.id).first()
        if profile:
            profile.industry = payload.industry
            profile.revenue_band = payload.revenue_band
            profile.employees = payload.employees
            profile.goals = payload.goals
            db.commit()
            db.refresh(profile)
            return profile
        profile = Profile(
            user_id=existing.id,
            industry=payload.industry,
            revenue_band=payload.revenue_band,
            employees=payload.employees,
            goals=payload.goals,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile
    return profile_service.create_profile(
        db,
        user_email=payload.user_email,
        password=payload.password,
        industry=payload.industry,
        revenue_band=payload.revenue_band,
        employees=payload.employees,
        goals=payload.goals,
    )


@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = profile_service.get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
