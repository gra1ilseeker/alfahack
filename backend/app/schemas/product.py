from typing import Optional, Any
from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    type: Optional[str] = None
    rate: Optional[float] = None
    min_limit: Optional[float] = None
    max_limit: Optional[float] = None
    requirements_json: Optional[Any] = None


class ProductResponse(ProductCreate):
    id: int

    class Config:
        from_attributes = True
