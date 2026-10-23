from datetime import datetime
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime | None = None


class LogoutResponse(BaseModel):
    detail: str = "logged out"


class DeleteAccountResponse(BaseModel):
    detail: str = "account deleted"
