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


class AccountProfileResponse(BaseModel):
    id: int
    industry: str | None = None
    revenue_band: str | None = None
    employees: int | None = None
    goals: str | None = None

    class Config:
        from_attributes = True


class AccountResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    profile: AccountProfileResponse | None = None

    class Config:
        from_attributes = True
