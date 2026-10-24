from typing import Any, List
from pydantic import BaseModel


class RankRequest(BaseModel):
    profile_id: int
    products: List[int]


class RankResponse(BaseModel):
    ranking_id: int
    result: Any
