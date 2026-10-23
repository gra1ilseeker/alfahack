from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session

from app.models import User, Profile
from app.schemas.auth import LoginRequest, TokenResponse, LogoutResponse, DeleteAccountResponse, AccountResponse, AccountProfileResponse
from app.services.auth import authenticate, create_user, create_session, delete_session_by_token
from app.services.auth import delete_sessions_by_user
from app.services.profile import delete_profile_and_user
from app.api.deps import get_db, get_current_session, get_current_user


class OAuth2PasswordRequestFormLoose:
    def __init__(
        self,
        username: str = Form(..., description="Email"),
        password: str = Form(...),
        grant_type: str | None = Form(None, description="password"),
        scope: str = Form(""),
        client_id: str | None = Form(None),
        client_secret: str | None = Form(None),
    ):
        self.username = username
        self.password = password
        self.scopes = scope.split()
        self.grant_type = grant_type
        self.client_id = client_id
        self.client_secret = client_secret

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    session = create_session(db, user.id)
    return TokenResponse(access_token=session.token, expires_at=session.expires_at)


@router.post("/token", response_model=TokenResponse, summary="OAuth2 password flow compatible")
def login_token(form_data: OAuth2PasswordRequestFormLoose = Depends(), db: Session = Depends(get_db)):
    # Swagger Authorize шлёт username=email, password — пароль
    user = authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    session = create_session(db, user.id)
    return TokenResponse(access_token=session.token, expires_at=session.expires_at)


@router.post("/register", response_model=TokenResponse)
def register(payload: LoginRequest, db: Session = Depends(get_db)):
    # проверяем по email, чтобы избежать уникального конфликта
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    user = create_user(db, payload.email, payload.password)
    session = create_session(db, user.id)
    return TokenResponse(access_token=session.token, expires_at=session.expires_at)


@router.post("/logout", response_model=LogoutResponse)
def logout(current_session=Depends(get_current_session), db: Session = Depends(get_db)):
    delete_session_by_token(db, current_session.token)
    return LogoutResponse()


@router.get("/me", response_model=AccountResponse)
def get_me(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    profile_payload = AccountProfileResponse.model_validate(profile) if profile else None
    return AccountResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        profile=profile_payload,
    )


@router.delete("/me", response_model=DeleteAccountResponse)
def delete_me(current_user=Depends(get_current_user), current_session=Depends(get_current_session), db: Session = Depends(get_db)):
    delete_sessions_by_user(db, current_user.id)
    delete_profile_and_user(db, current_user.id)
    return DeleteAccountResponse()
