from typing import Any
from pydantic import BaseModel


class DashboardResponse(BaseModel):
    profile_id: int
    summary: Any
    stability_index: float
