from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import authenticate, create_user
from app.api.deps import get_db

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = f"token-{user.id}"
    return TokenResponse(access_token=token)


@router.post("/register", response_model=TokenResponse)
def register(payload: LoginRequest, db: Session = Depends(get_db)):
    existing = authenticate(db, payload.email, payload.password)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    user = create_user(db, payload.email, payload.password)
    token = f"token-{user.id}"
    return TokenResponse(access_token=token)
