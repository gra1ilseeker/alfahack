from typing import Optional, List
from pydantic import BaseModel, EmailStr


class ProfileCreate(BaseModel):
    user_email: EmailStr
    password: str
    industry: Optional[str] = None
    revenue_band: Optional[str] = None
    employees: Optional[int] = None
    goals: Optional[str] = None


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    industry: Optional[str]
    revenue_band: Optional[str]
    employees: Optional[int]
    goals: Optional[str]

    class Config:
        from_attributes = True


class MetricItem(BaseModel):
    period: str
    revenue: float
    expenses: float
    cash_flow: float
    online_share: float = 0


class MetricsUpload(BaseModel):
    metrics: List[MetricItem]
